#!/usr/bin/env python3
"""
Module d'enrichissement du contexte pour le système RAG.
Permet d'améliorer la qualité des réponses en enrichissant le contexte avec des données
provenant de sources multiples et en adaptant le traitement selon le type de contenu.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import json
import numpy as np
import re

from .models import Document, LightningMetricsHistory, FeeChangeHypothesis, ChannelConfigHypothesis
from .mongo_operations import MongoOperations
from .embeddings.batch_embeddings import BatchEmbeddings
from .embeddings.vector_index import VectorIndex
from .utils.async_utils import async_timed, AsyncBatchProcessor, RetryWithBackoff

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedContextManager:
    """
    Gestionnaire de contexte amélioré pour la récupération augmentée de données
    avec support pour les requêtes hybrides, la pondération dynamique des sources
    et l'extraction automatique de contraintes.
    """
    
    def __init__(self, 
                 embedding_model="all-MiniLM-L6-v2",
                 vector_db_conn=None,
                 direct_db_conn=None):
        """
        Initialise le gestionnaire de contexte amélioré.
        
        Args:
            embedding_model: Modèle d'embedding à utiliser
            vector_db_conn: Connexion à la base de données vectorielle
            direct_db_conn: Connexion à la base de données principale
        """
        self.embedding_model = embedding_model
        self.vector_db_conn = vector_db_conn
        self.direct_db_conn = direct_db_conn
        
        # Collections supportées pour la recherche
        self.supported_collections = [
            "documents", "metrics", "node_data", "hypotheses", 
            "recommendations", "channel_data", "historical_analysis"
        ]
        
        # Mots-clés pour la détection des types de requêtes
        self.query_type_keywords = {
            "technical": ["comment", "fonctionne", "architecture", "conception", "technique", "implémentation"],
            "historical": ["historique", "évolution", "tendance", "passé", "précédent", "dernier", "durant"],
            "predictive": ["prévision", "recommandation", "suggestion", "hypothèse", "avis", "conseille", "stratégie"]
        }
        
        # Patterns pour la détection des contraintes
        self.node_id_pattern = r'(?:0[23])[a-fA-F0-9]{64,66}'  # LN Node ID pattern
        self.collection_keywords = {
            "metrics": ["métrique", "performance", "statistique", "mesure"],
            "hypotheses": ["hypothèse", "supposition", "théorie"],
            "channels": ["canal", "channel", "connexion", "lien"]
        }
        self.time_keywords = {
            "day": ["aujourd'hui", "jour", "24h", "dernières 24 heures"],
            "week": ["semaine", "7 jours", "hebdomadaire"],
            "month": ["mois", "30 jours", "mensuel"],
            "quarter": ["trimestre", "90 jours", "trimestriel"],
            "year": ["année", "an", "365 jours", "annuel"]
        }
    
    async def retrieve_enhanced_context(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Méthode principale pour récupérer le contexte enrichi pour une requête

        Args:
            query: Requête de l'utilisateur
            max_results: Nombre maximum de résultats à retourner

        Returns:
            Liste des résultats les plus pertinents avec pondération dynamique
        """
        # 1. Déterminer le type de requête
        query_type = self._determine_query_type(query)
        logger.info(f"Type de requête détecté: {query_type}")
        
        # 2. Extraire les contraintes de la requête
        constraints = self._extract_constraints_from_query(query)
        logger.info(f"Contraintes extraites: {constraints}")
        
        # 3. Effectuer une récupération hybride
        all_results = await self._hybrid_retrieval(query, constraints)
        logger.info(f"Récupération hybride: {len(all_results)} résultats trouvés")
        
        # 4. Appliquer la pondération dynamique des sources
        weighted_results = self._apply_dynamic_weighting(all_results, query_type, constraints)
        
        # 5. Trier par score et limiter le nombre de résultats
        sorted_results = sorted(weighted_results, key=lambda x: x.get("_score", 0), reverse=True)
        top_results = sorted_results[:max_results]
        
        return top_results
    
    def _determine_query_type(self, query: str) -> str:
        """
        Détermine le type de requête basé sur l'analyse de son contenu
        
        Args:
            query: Requête de l'utilisateur
            
        Returns:
            Type de requête: 'technical', 'historical' ou 'predictive'
        """
        query = query.lower()
        
        # Mots-clés techniques
        technical_keywords = [
            "comment", "fonctionne", "architecture", "protocole", "implémentation",
            "mécanisme", "technique", "fonctionnalité", "configurer", "design"
        ]
        
        # Mots-clés historiques
        historical_keywords = [
            "évolution", "historique", "tendance", "statistique", "performance",
            "dernier mois", "semaine dernière", "récent", "évolution", "passé"
        ]
        
        # Mots-clés prédictifs
        predictive_keywords = [
            "prédiction", "futur", "estimation", "recommandation", "suggère",
            "anticiper", "devrait", "pourrait", "tendance future", "perspective"
        ]
        
        # Compter les occurrences de chaque type de mots-clés
        tech_count = sum(1 for kw in technical_keywords if kw in query)
        hist_count = sum(1 for kw in historical_keywords if kw in query)
        pred_count = sum(1 for kw in predictive_keywords if kw in query)
        
        # Déterminer le type dominant
        if hist_count > tech_count and hist_count > pred_count:
            return "historical"
        elif pred_count > tech_count and pred_count > hist_count:
            return "predictive"
        else:
            # Par défaut, on considère que c'est une requête technique
            return "technical"
    
    def _extract_constraints_from_query(self, query: str) -> Dict[str, Any]:
        """
        Extrait automatiquement les contraintes implicites contenues dans la requête
        
        Args:
            query: Requête de l'utilisateur
            
        Returns:
            Dictionnaire des contraintes détectées
        """
        constraints = {}
        query_lower = query.lower()
        
        # Détection des identifiants de nœuds
        node_ids = re.findall(self.node_id_pattern, query)
        if node_ids:
            constraints["node_ids"] = node_ids
        
        # Détection des contraintes temporelles
        time_range = self._extract_time_range(query_lower)
        if time_range:
            constraints["time_range"] = time_range
        
        # Détection des collections spécifiques
        collection_filters = {}
        for collection, keywords in self.collection_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                collection_filters[collection] = True
        
        if collection_filters:
            constraints["collection_filters"] = collection_filters
        
        return constraints
    
    def _extract_time_range(self, query: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Extrait la plage temporelle à partir de la requête
        
        Args:
            query: Requête en minuscules
            
        Returns:
            Tuple (début, fin) de la plage temporelle ou None
        """
        now = datetime.now()
        
        # Détection de la période
        for period, keywords in self.time_keywords.items():
            if any(keyword in query for keyword in keywords):
                if period == "day":
                    start_date = now - timedelta(days=1)
                elif period == "week":
                    start_date = now - timedelta(days=7)
                elif period == "month":
                    start_date = now - timedelta(days=30)
                elif period == "quarter":
                    start_date = now - timedelta(days=90)
                elif period == "year":
                    start_date = now - timedelta(days=365)
                else:
                    continue
                
                return (start_date, now)
        
        # Si aucune période spécifique n'est détectée mais que des mots-clés temporels sont présents
        temporal_keywords = ["récent", "dernier", "passé", "ancien", "historique"]
        if any(keyword in query for keyword in temporal_keywords):
            # Par défaut, considérer le mois dernier
            return (now - timedelta(days=30), now)
        
        return None
    
    async def _hybrid_retrieval(self, query: str, constraints: Dict[str, Any]) -> List[Dict]:
        """
        Effectue une récupération hybride combinant recherche vectorielle et recherche directe en base de données
        
        Args:
            query: Requête de l'utilisateur
            constraints: Contraintes extraites de la requête
            
        Returns:
            Liste combinée de résultats
        """
        results = []
        
        # Toujours effectuer une recherche vectorielle
        vector_results = await self._vector_search(query, constraints)
        results.extend(vector_results)
        
        # Si des contraintes spécifiques sont présentes, effectuer une recherche directe
        if constraints:
            direct_results = await self._direct_db_retrieval(constraints)
            results.extend(direct_results)
        
        # Dédupliquer les résultats par _id
        unique_results = {}
        for result in results:
            result_id = result.get("_id", "")
            if result_id and (result_id not in unique_results or 
                              result.get("_score", 0) > unique_results[result_id].get("_score", 0)):
                unique_results[result_id] = result
        
        # Convertir le dictionnaire en liste
        combined_results = list(unique_results.values())
        return combined_results
    
    async def _vector_search(self, query: str, constraints: Dict[str, Any]) -> List[Dict]:
        """
        Effectue une recherche vectorielle sémantique
        
        Args:
            query: Requête de l'utilisateur
            constraints: Contraintes extraites
            
        Returns:
            Liste de résultats avec scores
        """
        # Note: Cette méthode serait implémentée pour intégrer avec un index vectoriel réel
        # Ici, c'est un placeholder pour le pattern
        return []
    
    async def _direct_db_retrieval(self, constraints: Dict[str, Any]) -> List[Dict]:
        """
        Effectue une récupération directe depuis la base de données en fonction des contraintes
        
        Args:
            constraints: Dictionnaire des contraintes pour la recherche
            
        Returns:
            Liste de documents correspondant aux contraintes
        """
        if not self.direct_db_conn:
            logger.warning("Aucune connexion à la base de données directe n'est disponible.")
            return []
            
        query_filters = {}
        results = []
        
        # Appliquer les contraintes temporelles si présentes
        if "time_range" in constraints:
            start_date, end_date = constraints["time_range"]
            query_filters["metadata.timestamp"] = {
                "$gte": start_date,
                "$lte": end_date
            }
        
        # Appliquer les contraintes de nœuds si présentes
        if "node_ids" in constraints:
            node_ids = constraints["node_ids"]
            # Selon la structure de la base de données, adapter cette partie
            query_filters["$or"] = [
                {"metadata.node_id": {"$in": node_ids}},
                {"content": {"$regex": "|".join(node_ids)}}
            ]
        
        # Déterminer les collections à interroger
        collections_to_search = []
        if "collection_filters" in constraints:
            # Ne rechercher que dans les collections spécifiées
            for collection, include in constraints["collection_filters"].items():
                if include and collection in self.supported_collections:
                    collections_to_search.append(collection)
        else:
            # Par défaut, rechercher dans toutes les collections supportées
            collections_to_search = self.supported_collections
            
        # Exécuter les requêtes sur les collections sélectionnées
        for collection in collections_to_search:
            try:
                collection_results = await self.direct_db_conn[collection].find(
                    query_filters
                ).limit(20).to_list(length=20)
                
                # Ajouter le nom de la collection aux métadonnées
                for doc in collection_results:
                    if "metadata" not in doc:
                        doc["metadata"] = {}
                    doc["metadata"]["collection"] = collection
                    results.extend(collection_results)
            except Exception as e:
                logger.error(f"Erreur lors de la recherche dans la collection {collection}: {e}")
                
        return results
    
    def _calculate_keyword_score(self, document: Dict, query: str) -> float:
        """
        Calcule un score basé sur les correspondances de mots-clés
        
        Args:
            document: Document à évaluer
            query: Requête de l'utilisateur
            
        Returns:
            Score entre 0 et 1
        """
        # Extraction des mots-clés de la requête (hors mots vides)
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        
        # Extraction du contenu du document
        content = document.get("content", "").lower()
        
        # Comptage des correspondances
        matches = sum(1 for word in query_words if word in content)
        
        # Calcul du score normalisé
        return min(1.0, matches / max(1, len(query_words))) if query_words else 0.0
    
    def _apply_dynamic_weighting(self, results: List[Dict], query_type: str, 
                               constraints: Dict[str, Any]) -> List[Dict]:
        """
        Applique une pondération dynamique aux résultats en fonction du type de requête
        
        Args:
            results: Liste des résultats à pondérer
            query_type: Type de requête détecté
            constraints: Contraintes extraites de la requête
            
        Returns:
            Liste des résultats avec scores ajustés
        """
        weighted_results = results.copy()
        
        # Facteurs de pondération selon le type de document et le type de requête
        type_weights = {
            "technical": {
                "document": 1.5,
                "metrics": 0.8,
                "node_data": 1.2,
                "hypotheses": 0.7,
                "recommendations": 0.9,
                "channel_data": 1.0,
                "historical_analysis": 0.8
            },
            "historical": {
                "document": 0.9,
                "metrics": 1.6,
                "node_data": 1.3,
                "hypotheses": 0.8,
                "recommendations": 0.7,
                "channel_data": 1.2,
                "historical_analysis": 1.5
            },
            "predictive": {
                "document": 0.7,
                "metrics": 1.0,
                "node_data": 0.9,
                "hypotheses": 1.7,
                "recommendations": 1.5,
                "channel_data": 1.1,
                "historical_analysis": 1.2
            }
        }
        
        # Facteur de pondération pour les résultats correspondant aux contraintes explicites
        constraint_boost = 1.3
        
        # Facteur de pondération pour les documents récents
        recency_boost = 1.2
        recency_threshold = datetime.now() - timedelta(days=7)
        
        for result in weighted_results:
            base_score = result.get("_score", 0.5)
            metadata = result.get("metadata", {})
            doc_type = metadata.get("type", "document")
            collection = metadata.get("collection", "documents")
            
            # 1. Appliquer la pondération selon le type de document et de requête
            type_weight = type_weights.get(query_type, {}).get(doc_type, 1.0)
            weighted_score = base_score * type_weight
            
            # 2. Boost pour les résultats correspondant aux contraintes
            if "node_ids" in constraints and metadata.get("node_id") in constraints["node_ids"]:
                weighted_score *= constraint_boost
                
            # 3. Boost pour les documents récents (si timestamp disponible)
            if "timestamp" in metadata:
                timestamp = metadata["timestamp"]
                if timestamp > recency_threshold:
                    weighted_score *= recency_boost
                    
            # 4. Ajustement en fonction de la spécificité des collections filtrées
            if "collection_filters" in constraints:
                if collection in constraints["collection_filters"]:
                    weighted_score *= constraint_boost
            
            # Mettre à jour le score
            result["_score"] = weighted_score
            
        return weighted_results

    def _compile_extraction_patterns(self):
        """Compile les patterns regex pour l'extraction de contraintes"""
        # Patterns temporels
        self.time_patterns = {
            r'\b(derni[èe]re|pass[ée]e)\s+semaine\b': (datetime.now() - timedelta(days=7), datetime.now()),
            r'\b(dernier|pass[ée])\s+mois\b': (datetime.now() - timedelta(days=30), datetime.now()),
            r'\b(derni[èe]re|pass[ée]e)\s+ann[ée]e\b': (datetime.now() - timedelta(days=365), datetime.now()),
            r'\bhier\b': (datetime.now() - timedelta(days=1), datetime.now()),
            r'\baujourd\'hui\b': (datetime.now() - timedelta(days=1), datetime.now()),
            r'\br[ée]cent\b': (datetime.now() - timedelta(days=14), datetime.now()),
            r'(depuis|il y a)\s+(\d+)\s+(jour|jours|semaine|semaines|mois|ann[ée]e|ann[ée]es)\b': None,  # Traité séparément
        }
        
        # Pattern d'ID de nœud Lightning (03... ou 02... suivi de 64 caractères hex)
        self.node_id_pattern = re.compile(r'0[23][a-f0-9]{64}')
        
        # Patterns de types de requêtes
        self.query_type_patterns = {
            "technical": [
                r'comment\s+(fonctionne|marche|utiliser|impl[ée]menter)',
                r'qu\'est[\-\s]ce\s+que',
                r'expliquer?',
                r'd[ée]finir?',
                r'architecture'
            ],
            "historical": [
                r'(historique|[ée]volution)',
                r'(avant|apr[èe]s)',
                r'(pass[ée]|pr[ée]c[ée]dent)',
                r'tendance',
                r'changement'
            ],
            "predictive": [
                r'pr[ée]dire',
                r'futur',
                r'anticiper',
                r'recommand(er|ation)',
                r'sugg[ée]rer',
                r'devrait',
                r'optimiser'
            ]
        }
        
        # Compilation des patterns
        for query_type, patterns in self.query_type_patterns.items():
            self.query_type_patterns[query_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
    async def initialize(self):
        """Initialise le gestionnaire et charge les index existants"""
        # Création des dossiers pour les index
        os.makedirs("data/indexes", exist_ok=True)
        
        # Tentative de chargement des index existants
        for index_name in self.vector_indexes:
            index_path = f"data/indexes/{index_name}_index"
            if os.path.exists(f"{index_path}.meta"):
                try:
                    self.vector_indexes[index_name] = VectorIndex.load(index_path)
                    logger.info(f"Index vectoriel '{index_name}' chargé avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement de l'index '{index_name}': {str(e)}")
        
        return self
    
    async def build_unified_index(self) -> bool:
        """
        Construit un index unifié à partir de toutes les sources de données.
        
        Returns:
            True si succès, False sinon
        """
        try:
            start_time = datetime.now()
            
            # Récupération des documents de différentes sources
            documents = await self._get_documents_from_all_sources()
            
            if not documents:
                logger.warning("Aucun document trouvé pour construire l'index unifié")
                return False
            
            logger.info(f"Construction de l'index unifié avec {len(documents)} documents")
            
            # Création des chunks adaptés selon le type de contenu
            all_chunks = []
            for doc in documents:
                doc_type = doc.get("metadata", {}).get("type", "document")
                chunking_strategy = self.chunking_strategies.get(doc_type, self._standard_chunking)
                chunks = chunking_strategy(doc)
                all_chunks.extend(chunks)
            
            logger.info(f"Génération d'embeddings pour {len(all_chunks)} chunks")
            
            # Traitement par lots des chunks
            async def process_chunk_batch(chunk_batch: List[Dict]) -> List[Dict]:
                texts = [self._get_embedding_text(chunk) for chunk in chunk_batch]
                embeddings = await self.batch_embeddings.get_embeddings_with_retry(texts)
                
                processed_chunks = []
                for i, (chunk, embedding) in enumerate(zip(chunk_batch, embeddings)):
                    chunk["embedding"] = embedding
                    processed_chunks.append(chunk)
                
                return processed_chunks
            
            # Traitement parallèle des chunks
            processed_chunks = await self.batch_processor.process_batches_parallel(
                all_chunks, 
                process_chunk_batch
            )
            
            # Ajout à l'index unifié
            chunk_embeddings = [chunk["embedding"] for chunk in processed_chunks]
            self.vector_indexes["unified"].add_documents(processed_chunks, chunk_embeddings)
            
            # Sauvegarde de l'index
            self.vector_indexes["unified"].save("data/indexes/unified_index")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Index unifié construit en {processing_time:.2f} secondes")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction de l'index unifié: {str(e)}")
            return False
    
    async def retrieve_enhanced_context(
        self, 
        query: str, 
        k: int = 5,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        node_ids: Optional[List[str]] = None,
        collection_filters: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère un contexte enrichi pour une requête en combinant différentes sources.
        
        Args:
            query: Texte de la requête
            k: Nombre de documents à récupérer
            time_range: Plage temporelle optionnelle (début, fin)
            node_ids: Liste optionnelle d'IDs de nœuds à filtrer
            collection_filters: Filtres optionnels par collection (ex: {"metrics": True, "hypotheses": False})
            
        Returns:
            Liste des documents de contexte
        """
        try:
            # Extraction des contraintes depuis la requête
            extracted_constraints = self._extract_constraints_from_query(query)
            
            # Fusion des contraintes explicites et extraites
            if not time_range and "time_range" in extracted_constraints:
                time_range = extracted_constraints["time_range"]
            
            if not node_ids and "node_ids" in extracted_constraints:
                node_ids = extracted_constraints["node_ids"]
            
            if not collection_filters and "collection_filters" in extracted_constraints:
                collection_filters = extracted_constraints["collection_filters"]
            
            # Détermination du type de requête pour la pondération
            query_type = self._determine_query_type(query)
            logger.info(f"Type de requête détecté: {query_type}")
            
            # Utilisation de la récupération hybride
            results = await self._hybrid_retrieval(
                query=query,
                k=k*2,  # Récupérer plus pour filtrer et re-trier
                time_range=time_range,
                node_ids=node_ids,
                collection_filters=collection_filters,
                query_type=query_type
            )
            
            # Tri final par score
            results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            return results[:k]
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du contexte enrichi: {str(e)}")
            return []
    
    async def _hybrid_retrieval(
        self,
        query: str,
        k: int = 10,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        node_ids: Optional[List[str]] = None,
        collection_filters: Optional[Dict[str, bool]] = None,
        query_type: str = "technical"
    ) -> List[Dict[str, Any]]:
        """
        Effectue une récupération hybride combinant recherche vectorielle, filtrage temporel et métadonnées.
        
        Args:
            query: Texte de la requête
            k: Nombre de documents à récupérer
            time_range: Plage temporelle (début, fin)
            node_ids: Liste d'IDs de nœuds à filtrer
            collection_filters: Filtres par collection
            query_type: Type de requête ("technical", "historical", "predictive")
            
        Returns:
            Liste des documents de contexte avec scores combinés
        """
        # Obtention de l'embedding de la requête
        query_embedding = await self.retry_manager.execute(
            self.batch_embeddings.embeddings.embed_query,
            query
        )
        
        # Récupération vectorielle de base (recherche sémantique)
        vector_results = self.vector_indexes["unified"].search(query_embedding, k=k*3)  # Récupérer plus pour filtrage
        
        # Filtrage et scoring des résultats
        filtered_results = []
        source_weights = self.source_weights.get(query_type, self.source_weights["technical"])
        
        for doc, vector_score in vector_results:
            # Initialisation du score final
            final_score = vector_score
            
            # Appliquer le poids selon la source
            doc_type = doc.get("metadata", {}).get("type", "document")
            source_type = "documents"  # Par défaut
            
            if doc_type == "metrics_history":
                source_type = "metrics"
            elif doc_type == "hypothesis_result":
                source_type = "hypotheses"
            
            source_weight = source_weights.get(source_type, 1.0)
            final_score *= source_weight
            
            # Bonus temporel pour les résultats récents si recherche historique
            if time_range and "timestamp" in doc:
                doc_time = doc["timestamp"]
                if isinstance(doc_time, str):
                    doc_time = datetime.fromisoformat(doc_time.replace("Z", "+00:00"))
                
                if doc_time < time_range[0] or doc_time > time_range[1]:
                    continue  # Hors de la plage temporelle
                
                # Plus proche du temps présent = score plus élevé (pour requêtes récentes)
                if query_type == "historical":
                    time_factor = (doc_time - time_range[0]).total_seconds() / (time_range[1] - time_range[0]).total_seconds()
                    final_score *= (0.7 + 0.3 * time_factor)  # Boost de 30% max pour les plus récents
            
            # Filtrage par nœud
            if node_ids and "node_id" in doc and doc["node_id"] not in node_ids:
                continue
            
            # Filtrage par collection
            if collection_filters:
                if doc_type == "metrics_history" and not collection_filters.get("metrics", True):
                    continue
                if doc_type == "hypothesis_result" and not collection_filters.get("hypotheses", True):
                    continue
                if doc_type == "document" and not collection_filters.get("documents", True):
                    continue
            
            # Bonus pour les documents ayant des mots-clés spécifiques
            keyword_score = self._calculate_keyword_score(doc.get("content", ""), query)
            final_score += keyword_score * 0.2  # 20% d'influence max
            
            # Ajouter les scores à l'objet document
            doc["similarity_score"] = vector_score
            doc["source_weight"] = source_weight
            doc["keyword_score"] = keyword_score
            doc["final_score"] = final_score
            
            filtered_results.append(doc)
            
            # Limiter au nombre demandé après tout le traitement
            if len(filtered_results) >= k:
                break
        
        # Incorporer des résultats de requêtes DB directes pour les requêtes temporelles/spécifiques
        if (time_range or node_ids) and len(filtered_results) < k:
            # Requête directe à MongoDB pour compléter si nécessaire
            direct_results = await self._direct_db_retrieval(
                query=query,
                time_range=time_range,
                node_ids=node_ids,
                collection_filters=collection_filters,
                limit=k - len(filtered_results)
            )
            
            # Ajouter un score estimé aux résultats directs
            for doc in direct_results:
                doc_type = doc.get("metadata", {}).get("type", "document") 
                source_type = "documents"
                if doc_type == "metrics_history":
                    source_type = "metrics"
                elif doc_type == "hypothesis_result":
                    source_type = "hypotheses"
                
                source_weight = source_weights.get(source_type, 1.0)
                # Score arbitraire pour les résultats directs (légèrement inférieur aux résultats vectoriels)
                default_similarity = 0.7
                final_score = default_similarity * source_weight
                
                # Bonus pour les documents ayant des mots-clés spécifiques
                keyword_score = self._calculate_keyword_score(doc.get("content", ""), query)
                final_score += keyword_score * 0.2
                
                doc["similarity_score"] = default_similarity
                doc["source_weight"] = source_weight
                doc["keyword_score"] = keyword_score
                doc["final_score"] = final_score
                
                filtered_results.append(doc)
        
        return filtered_results
    
    def _calculate_keyword_score(self, content: str, query: str) -> float:
        """
        Calcule un score basé sur la présence de mots-clés de la requête dans le contenu.
        
        Args:
            content: Contenu du document
            query: Texte de la requête
            
        Returns:
            Score entre 0 et 1
        """
        if not content or not query:
            return 0.0
        
        # Extraction des mots significatifs de la requête (mots de plus de 3 lettres)
        query_words = [word.lower() for word in re.findall(r'\b\w{4,}\b', query)]
        if not query_words:
            return 0.0
        
        # Calcul du nombre de mots-clés présents dans le contenu
        matches = 0
        content_lower = content.lower()
        for word in query_words:
            if word in content_lower:
                matches += 1
        
        # Score basé sur le ratio de mots-clés trouvés
        return matches / len(query_words)
    
    async def _direct_db_retrieval(
        self,
        query: str,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        node_ids: Optional[List[str]] = None,
        collection_filters: Optional[Dict[str, bool]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Effectue une récupération directe depuis MongoDB pour compléter les résultats vectoriels.
        
        Args:
            query: Texte de la requête
            time_range: Plage temporelle (début, fin)
            node_ids: Liste d'IDs de nœuds à filtrer
            collection_filters: Filtres par collection
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des documents de contexte
        """
        results = []
        
        try:
            # Récupération de métriques si autorisé
            if not collection_filters or collection_filters.get("metrics", True):
                metrics_filter = {}
                if time_range:
                    metrics_filter["timestamp"] = {"$gte": time_range[0], "$lte": time_range[1]}
                if node_ids:
                    metrics_filter["node_id"] = {"$in": node_ids}
                
                if metrics_filter:
                    metrics_docs = await self.mongo_ops.db.metrics_history.find(
                        metrics_filter
                    ).sort("timestamp", -1).limit(limit // 2).to_list(length=limit // 2)
                    
                    # Conversion des documents métriques pour la cohérence de format
                    for doc in metrics_docs:
                        formatted_doc = self._metric_focused_chunking(doc)[0]
                        results.append(formatted_doc)
            
            # Récupération d'hypothèses si autorisé
            if not collection_filters or collection_filters.get("hypotheses", True):
                hypothesis_filter = {"is_validated": {"$ne": None}}
                if node_ids:
                    hypothesis_filter["node_id"] = {"$in": node_ids}
                
                hypothesis_docs = await self.mongo_ops.db.fee_hypotheses.find(
                    hypothesis_filter
                ).sort("created_at", -1).limit(limit // 2).to_list(length=limit // 2)
                
                # Conversion des documents d'hypothèses pour la cohérence de format
                for doc in hypothesis_docs:
                    formatted_chunks = self._hypothesis_chunking(doc)
                    results.extend(formatted_chunks)
                
                # Limiter si nécessaire
                if len(results) > limit:
                    results = results[:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération directe: {str(e)}")
            return []
    
    def _standard_chunking(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Stratégie de chunking standard pour les documents textuels.
        
        Args:
            document: Document à découper
            
        Returns:
            Liste des chunks
        """
        content = document.get("content", "")
        if not content:
            return []
        
        # Chunking par paragraphes avec chevauchement
        paragraphs = content.split("\n\n")
        chunks = []
        
        # Fenêtre glissante sur les paragraphes (3 par chunk, décalage de 1)
        for i in range(0, len(paragraphs)):
            # Prendre 3 paragraphes consécutifs, ou moins s'il n'y en a pas assez
            window_end = min(i + 3, len(paragraphs))
            window_text = "\n\n".join(paragraphs[i:window_end])
            
            # Vérifier que le chunk a une taille minimale
            if len(window_text.strip()) < 10:
                continue
            
            # Créer le chunk
            chunk = document.copy()
            chunk["content"] = window_text
            chunk["chunk_index"] = i
            chunk["metadata"] = chunk.get("metadata", {}).copy()
            chunk["metadata"]["chunk_type"] = "standard"
            
            chunks.append(chunk)
            
            # Si c'est le dernier groupe de paragraphes, arrêter
            if window_end == len(paragraphs):
                break
        
        return chunks
    
    def _metric_focused_chunking(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Stratégie de chunking pour les métriques historiques.
        
        Args:
            document: Document de métriques à découper
            
        Returns:
            Liste des chunks
        """
        # Les métriques sont déjà bien structurées, créer un seul chunk par période
        if "content" not in document:
            # Pour les documents de métriques avec structure JSON
            metrics_data = document.copy()
            # Créer une représentation textuelle des métriques
            content = f"Métriques pour le nœud {metrics_data.get('node_id', 'inconnu')}\n"
            content += f"Date: {metrics_data.get('timestamp', 'inconnue')}\n"
            
            # Ajouter les métriques disponibles
            for key, value in metrics_data.items():
                if key not in ["node_id", "timestamp", "metadata", "_id"]:
                    content += f"{key}: {value}\n"
            
            chunk = {
                "content": content,
                "node_id": metrics_data.get("node_id"),
                "timestamp": metrics_data.get("timestamp"),
                "metadata": {
                    "type": "metrics_history",
                    "chunk_type": "metrics",
                    "source": "metrics_history"
                }
            }
            return [chunk]
        else:
            # Pour les documents textuels contenant des métriques
            return self._standard_chunking(document)
    
    def _hypothesis_chunking(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Stratégie de chunking pour les résultats d'hypothèses.
        
        Args:
            document: Document d'hypothèse à découper
            
        Returns:
            Liste des chunks
        """
        # Extraction des informations clés de l'hypothèse
        hypothesis_data = document.copy()
        
        # Création d'un chunk pour les informations générales
        general_content = f"Hypothèse ID: {hypothesis_data.get('hypothesis_id', 'inconnu')}\n"
        general_content += f"Nœud: {hypothesis_data.get('node_id', 'inconnu')}\n"
        general_content += f"Créée le: {hypothesis_data.get('created_at', 'inconnue')}\n"
        general_content += f"Validée: {hypothesis_data.get('is_validated', 'non évaluée')}\n"
        general_content += f"Conclusion: {hypothesis_data.get('conclusion', 'non disponible')}\n"
        
        general_chunk = {
            "content": general_content,
            "node_id": hypothesis_data.get("node_id"),
            "timestamp": hypothesis_data.get("created_at"),
            "metadata": {
                "type": "hypothesis_result",
                "chunk_type": "hypothesis_general",
                "source": "hypothesis"
            }
        }
        
        # Création d'un chunk pour les métriques d'impact si disponibles
        impact_chunks = []
        if "impact_metrics" in hypothesis_data and hypothesis_data["impact_metrics"]:
            impact_content = f"Métriques d'impact pour l'hypothèse {hypothesis_data.get('hypothesis_id', 'inconnue')}:\n"
            
            for key, value in hypothesis_data["impact_metrics"].items():
                impact_content += f"{key}: {value}\n"
            
            impact_chunk = {
                "content": impact_content,
                "node_id": hypothesis_data.get("node_id"),
                "timestamp": hypothesis_data.get("evaluation_completed_at", hypothesis_data.get("created_at")),
                "metadata": {
                    "type": "hypothesis_result",
                    "chunk_type": "hypothesis_impact",
                    "source": "hypothesis"
                }
            }
            impact_chunks.append(impact_chunk)
        
        return [general_chunk] + impact_chunks
    
    def _get_embedding_text(self, chunk: Dict[str, Any]) -> str:
        """
        Extrait le texte à utiliser pour l'embedding d'un chunk.
        Enrichit le texte avec des métadonnées pertinentes.
        
        Args:
            chunk: Chunk à traiter
            
        Returns:
            Texte enrichi pour l'embedding
        """
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        
        # Enrichissement selon le type de document
        prefix = ""
        if metadata.get("type") == "metrics_history":
            node_id = chunk.get("node_id", "")
            timestamp = chunk.get("timestamp", "")
            prefix = f"Métriques Lightning pour le nœud {node_id} à {timestamp}. "
        
        elif metadata.get("type") == "hypothesis_result":
            if metadata.get("chunk_type") == "hypothesis_general":
                prefix = "Résumé d'une hypothèse de validation Lightning Network. "
            elif metadata.get("chunk_type") == "hypothesis_impact":
                prefix = "Métriques d'impact d'une hypothèse Lightning Network. "
        
        # Texte final enrichi
        return prefix + content
    
    async def _get_documents_from_all_sources(self) -> List[Dict[str, Any]]:
        """
        Récupère les documents de toutes les sources disponibles.
        
        Returns:
            Liste de tous les documents
        """
        all_docs = []
        
        # 1. Récupération des documents textuels
        text_docs = await self.mongo_ops.get_all_documents()
        all_docs.extend(text_docs)
        
        # 2. Récupération des métriques historiques (échantillon représentatif)
        # Pour éviter de surcharger la mémoire, on limite à un échantillon
        metrics_query = {"timestamp": {"$gt": datetime.now() - timedelta(days=90)}}
        metrics_docs = await self.mongo_ops.db.metrics_history.find(metrics_query).limit(1000).to_list(length=1000)
        all_docs.extend(metrics_docs)
        
        # 3. Récupération des hypothèses validées
        fee_hypotheses = await self.mongo_ops.db.fee_hypotheses.find(
            {"is_validated": {"$ne": None}}
        ).limit(500).to_list(length=500)
        all_docs.extend(fee_hypotheses)
        
        channel_hypotheses = await self.mongo_ops.db.channel_hypotheses.find(
            {"is_validated": {"$ne": None}}
        ).limit(500).to_list(length=500)
        all_docs.extend(channel_hypotheses)
        
        return all_docs 