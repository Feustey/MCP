"""
Module de workflow RAG augmenté avec pondération dynamique des sources et contraintes avancées.

Ce module étend le workflow RAG standard avec les capacités avancées de récupération
du AugmentedRetrievalManager pour offrir des réponses plus précises et contextualisées.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from src.enhanced_rag import EnhancedRAGWorkflow
from src.enhanced_retrieval import AugmentedRetrievalManager
from src.redis_operations import RedisOperations

# Configuration du logging
logger = logging.getLogger(__name__)

class AugmentedRAGWorkflow(EnhancedRAGWorkflow):
    """
    Workflow RAG augmenté qui exploite les capacités avancées de récupération contextuelle.
    Intègre pondération dynamique des sources, extraction avancée de contraintes et
    historique des requêtes pour améliorer la qualité des réponses.
    """
    
    def __init__(self, 
                 model_name="gpt-4", 
                 embedding_model="all-MiniLM-L6-v2",
                 redis_ops: Optional[RedisOperations] = None,
                 *args, **kwargs):
        """
        Initialise le workflow RAG augmenté.
        
        Args:
            model_name: Nom du modèle LLM à utiliser
            embedding_model: Modèle d'embedding à utiliser
            redis_ops: Instance de RedisOperations pour le cache (optionnel)
            *args, **kwargs: Arguments additionnels pour le workflow parent
        """
        super().__init__(model_name=model_name, embedding_model=embedding_model, 
                       redis_ops=redis_ops, *args, **kwargs)
        
        # Remplacer le gestionnaire de contexte standard par sa version augmentée
        self.context_manager = AugmentedRetrievalManager(
            embedding_model=embedding_model,
            vector_db_conn=self.vector_db_conn,
            direct_db_conn=self.mongo_ops.db if hasattr(self, 'mongo_ops') else None
        )
        
        # Configuration avancée
        self.enable_dynamic_weighting = True
        self.dynamic_prompt_templates = {
            "technical": "Voici des informations techniques sur {query_subject}: {context}\n\nRépondez à cette question technique: {query}",
            "historical": "Voici des données historiques concernant {query_subject}: {context}\n\nRépondez à cette question sur l'historique: {query}",
            "predictive": "Voici des informations pertinentes pour établir une prédiction: {context}\n\nRépondez à cette demande de prédiction: {query}"
        }
    
    async def initialize(self):
        """Initialise le workflow et ses composants"""
        await super().initialize()
        # Initialisation spécifique pour le gestionnaire augmenté
        if hasattr(self.context_manager, '_compile_extraction_patterns'):
            self.context_manager._compile_extraction_patterns()
        return self
    
    async def query_augmented(self, 
                           query: str, 
                           top_k: int = 5,
                           dynamic_weighting: bool = True,
                           use_adaptive_prompt: bool = True,
                           cache_ttl: int = 3600,
                           *args, **kwargs) -> Dict[str, Any]:
        """
        Exécute une requête en utilisant le workflow RAG augmenté.
        
        Args:
            query: Texte de la requête
            top_k: Nombre de documents de contexte à récupérer
            dynamic_weighting: Utiliser la pondération dynamique des sources
            use_adaptive_prompt: Adapter le prompt selon le type de requête
            cache_ttl: Durée de vie du cache en secondes (3600 par défaut)
            *args, **kwargs: Paramètres additionnels pour la méthode parent
            
        Returns:
            Résultat de la requête avec métadonnées enrichies
        """
        # Vérifier le cache si disponible
        cache_key = f"aug_rag:{query}"
        if self.redis_ops:
            cached_result = await self.redis_ops.get_json(cache_key)
            if cached_result:
                logger.info(f"Résultat trouvé dans le cache pour: {query[:50]}...")
                cached_result["from_cache"] = True
                return cached_result
        
        try:
            # Extraction du sujet principal de la requête pour le prompt adaptatif
            query_subject = self._extract_query_subject(query)
            
            # Détermination du type de requête si prompt adaptatif activé
            query_type = "technical"  # valeur par défaut
            if use_adaptive_prompt:
                query_type = self.context_manager._determine_query_type(query)
            
            # Récupération du contexte enrichi avec pondération dynamique
            context_docs = await self.context_manager.retrieve_enhanced_context(
                query=query,
                limit=top_k,
                dynamic_weighting=dynamic_weighting,
                *args, **kwargs
            )
            
            # Formatage du contexte
            formatted_context = self._format_context_documents(context_docs)
            
            # Sélection du template de prompt selon le type de requête
            prompt_template = self.dynamic_prompt_templates.get(
                query_type, self.dynamic_prompt_templates["technical"]
            )
            
            # Génération du prompt final
            prompt = prompt_template.format(
                query=query,
                context=formatted_context,
                query_subject=query_subject
            )
            
            # Appel du modèle pour générer la réponse
            response = await self._generate_response(prompt)
            
            # Construction du résultat final
            result = {
                "query": query,
                "response": response,
                "context_documents": context_docs,
                "query_type": query_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "dynamic_weighting": dynamic_weighting,
                    "top_k": top_k,
                    "source_weights": getattr(self.context_manager, 'source_weights', {}),
                    "prompt_type": query_type
                }
            }
            
            # Mise en cache si Redis est disponible
            if self.redis_ops:
                # Créer des tags pour l'invalidation ciblée
                tags = [f"query_type:{query_type}"]
                
                # Ajouter des tags pour les collections utilisées
                for doc in context_docs:
                    source = doc.get("metadata", {}).get("source", "unknown")
                    if source not in tags:
                        tags.append(f"source:{source}")
                
                # Mise en cache avec les tags
                await self.redis_ops.set_json(cache_key, result, ex=cache_ttl, tags=tags)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la requête augmentée: {str(e)}")
            raise
    
    def _extract_query_subject(self, query: str) -> str:
        """
        Extrait le sujet principal de la requête pour personnalisation du prompt.
        
        Args:
            query: Texte de la requête
            
        Returns:
            Sujet principal de la requête
        """
        # Logique simplifiée - en pratique, on pourrait utiliser NLP plus avancé
        # Éliminer les mots interrogatifs courants et prendre le début
        query_lower = query.lower()
        
        # Mots à filtrer au début de la question
        filter_starts = [
            "qu'est-ce que", "qu'est ce que", "comment", "pourquoi", "quand",
            "où", "qui", "quel", "quelle", "quels", "quelles", "est-ce que",
            "est ce que", "pouvez-vous", "peux-tu", "donnez-moi", "donne-moi"
        ]
        
        # Supprimer les mots interrogatifs au début
        cleaned_query = query_lower
        for start in filter_starts:
            if query_lower.startswith(start):
                cleaned_query = query_lower[len(start):].strip()
                break
        
        # Extraire les premiers mots significatifs (au maximum 5)
        words = cleaned_query.split()
        significant_words = [w for w in words if len(w) > 3][:5]
        
        if significant_words:
            return " ".join(significant_words)
        else:
            # Fallback: premiers mots de la requête originale
            return " ".join(query.split()[:3])
    
    def _format_context_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        Formate les documents de contexte pour inclusion dans le prompt.
        Applique un formatage adapté au type de document.
        
        Args:
            documents: Liste des documents de contexte
            
        Returns:
            Contexte formaté
        """
        if not documents:
            return "Aucune information contextuelle disponible."
        
        formatted_sections = []
        
        for i, doc in enumerate(documents):
            metadata = doc.get("metadata", {})
            doc_type = metadata.get("type", "document")
            content = doc.get("content", "").strip()
            
            if not content:
                continue
            
            # Formatage adapté selon le type de document
            if doc_type == "metrics_history":
                header = f"[Métriques {i+1}] "
                # Format tabulaire pour les métriques
                formatted_sections.append(f"{header}{content}")
            
            elif doc_type == "hypothesis_result":
                header = f"[Hypothèse {i+1}] "
                # Mise en évidence des conclusions pour les hypothèses
                formatted_sections.append(f"{header}{content}")
            
            else:
                # Format standard pour les documents textuels
                header = f"[Document {i+1}] "
                formatted_sections.append(f"{header}{content}")
        
        # Assembler le tout avec séparateurs clairs
        return "\n\n".join(formatted_sections)
    
    async def invalidate_cache_by_tag(self, tag: str) -> int:
        """
        Invalide le cache par tag.
        
        Args:
            tag: Tag à invalider (ex: "source:metrics_history")
            
        Returns:
            Nombre d'entrées invalidées
        """
        if not self.redis_ops:
            return 0
        
        return await self.redis_ops.delete_by_tag(tag)
    
    async def refresh_source_weights(self, query_sample: List[str] = None) -> Dict[str, float]:
        """
        Rafraîchit les poids des sources en analysant des requêtes d'exemple.
        
        Args:
            query_sample: Échantillon de requêtes représentatives
            
        Returns:
            Poids des sources mis à jour
        """
        if not hasattr(self.context_manager, '_adjust_source_weights'):
            return {}
        
        if not query_sample:
            # Requêtes par défaut couvrant différents types
            query_sample = [
                "Comment fonctionne le routage dans le réseau Lightning?",
                "Quelle est l'évolution des frais de transaction sur les derniers mois?",
                "Quelles hypothèses ont été validées concernant les frais optimaux?",
                "Où puis-je trouver la documentation sur la configuration des canaux?"
            ]
        
        # Analyser chaque requête pour ajuster les poids
        for query in query_sample:
            constraints = self.context_manager._advanced_constraint_extraction(query)
            self.context_manager._adjust_source_weights(query, constraints)
        
        return self.context_manager.source_weights 