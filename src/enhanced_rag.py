#!/usr/bin/env python3
"""
Module RAG amélioré avec enrichissement du contexte.
Étend le RAGWorkflow standard pour offrir des capacités améliorées de récupération
et de contextualisation en exploitant diverses sources de données.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from .rag import RAGWorkflow, RAGError
from .mongo_operations import MongoOperations
from .redis_operations import RedisOperations
from .context_enrichment import EnhancedContextManager
from .utils.async_utils import async_timed

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRAGWorkflow(RAGWorkflow):
    """
    Version étendue du RAGWorkflow avec capacités d'enrichissement du contexte.
    Permet d'exploiter efficacement toutes les sources de données disponibles.
    """
    
    def __init__(
        self,
        redis_ops: Optional[RedisOperations] = None,
        similarity_top_k: int = 3,
        streaming: bool = True,
        use_unified_index: bool = True
    ):
        """
        Initialise le RAG amélioré avec enrichissement du contexte.
        
        Args:
            redis_ops: Instance optionnelle de RedisOperations
            similarity_top_k: Nombre de documents similaires à récupérer
            streaming: Utiliser le streaming pour les réponses
            use_unified_index: Utiliser l'index unifié (recommandé)
        """
        # Initialisation du RAGWorkflow standard
        super().__init__(redis_ops, similarity_top_k, streaming)
        
        # Initialisation du gestionnaire de contexte enrichi
        self.context_manager = EnhancedContextManager(
            mongo_ops=self.mongo_ops,
            batch_embeddings=self.batch_embeddings,
            dimension=1536
        )
        
        self.use_unified_index = use_unified_index
        self._init_enhanced_task = None
    
    async def initialize(self):
        """Initialise le workflow RAG amélioré et prépare l'index unifié si nécessaire"""
        # Initialisation du RAG standard
        await super().ensure_connected()
        
        # Initialisation du gestionnaire de contexte enrichi
        await self.context_manager.initialize()
        
        # Vérification et construction de l'index unifié si nécessaire
        if self.use_unified_index:
            index_path = "data/indexes/unified_index.meta"
            if not os.path.exists(index_path):
                logger.info("Construction de l'index unifié (première initialisation)...")
                await self.context_manager.build_unified_index()
        
        return self
    
    @async_timed()
    async def query_enhanced(
        self,
        query_text: str,
        top_k: int = 5,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        node_ids: Optional[List[str]] = None,
        collection_filters: Optional[Dict[str, bool]] = None
    ) -> str:
        """
        Exécute une requête RAG avec enrichissement du contexte.
        
        Args:
            query_text: Texte de la requête
            top_k: Nombre de documents de contexte à récupérer
            time_range: Plage temporelle optionnelle (début, fin)
            node_ids: Liste optionnelle d'IDs de nœuds à filtrer
            collection_filters: Filtres optionnels par collection
            
        Returns:
            Réponse générée
        """
        if not query_text:
            raise RAGError("Le texte de la requête ne peut pas être vide.")
        
        try:
            start_time = datetime.now()
            
            # Récupération du contexte enrichi
            enhanced_context = await self.context_manager.retrieve_enhanced_context(
                query=query_text,
                k=top_k,
                time_range=time_range,
                node_ids=node_ids,
                collection_filters=collection_filters
            )
            
            # Vérifier le cache intelligent si disponible
            if self.smart_cache:
                # Clé unique pour cette requête spécifique avec ses paramètres
                cache_key = {
                    "query": query_text,
                    "top_k": top_k,
                    "time_filter": str(time_range) if time_range else None,
                    "node_filter": str(node_ids) if node_ids else None
                }
                
                # Tentative de récupération depuis le cache
                cached_response = await self.smart_cache.get("enhanced_responses", cache_key)
                if cached_response:
                    logger.info(f"Réponse enrichie récupérée du cache pour: {query_text[:50]}...")
                    
                    # Mise à jour des statistiques pour le cache hit
                    await self._update_stats_for_cache_hit()
                    return cached_response
            
            # Adaptation du contexte pour le prompt
            context_text = self._format_enhanced_context(enhanced_context)
            
            # Construction du prompt enrichi
            prompt = self._build_enhanced_prompt(query_text, context_text)
            
            # Génération de la réponse avec le modèle de langage
            response = await self._generate_completion(prompt)
            
            # Mise en cache de la réponse si disponible
            if self.smart_cache:
                # Création de tags spécifiques pour cette requête
                tags = self._generate_context_tags(enhanced_context)
                
                await self.smart_cache.set(
                    "enhanced_responses",
                    cache_key,
                    response,
                    tags=tags
                )
            
            # Enregistrement de l'historique et mise à jour des statistiques
            await self._save_query_history(query_text, enhanced_context, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la requête RAG enrichie: {str(e)}")
            # Fallback vers la méthode standard en cas d'erreur
            logger.info("Utilisation du RAG standard comme fallback...")
            return await super().query(query_text, top_k)
    
    async def refresh_unified_index(self) -> bool:
        """
        Rafraîchit l'index unifié avec les données les plus récentes.
        
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info("Rafraîchissement de l'index unifié...")
            result = await self.context_manager.build_unified_index()
            logger.info(f"Rafraîchissement de l'index unifié {'réussi' if result else 'échoué'}")
            return result
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement de l'index unifié: {str(e)}")
            return False
    
    def _format_enhanced_context(self, context_documents: List[Dict[str, Any]]) -> str:
        """
        Formate les documents de contexte enrichi pour le prompt.
        
        Args:
            context_documents: Liste des documents de contexte
            
        Returns:
            Contexte formaté
        """
        if not context_documents:
            return "Aucun contexte pertinent trouvé."
        
        # Tri par type de document pour une meilleure organisation
        context_documents.sort(key=lambda x: x.get("metadata", {}).get("type", "z"))
        
        formatted_sections = []
        
        # Regroupement par type
        document_types = {}
        for doc in context_documents:
            doc_type = doc.get("metadata", {}).get("type", "document")
            if doc_type not in document_types:
                document_types[doc_type] = []
            document_types[doc_type].append(doc)
        
        # Formatage par type
        for doc_type, docs in document_types.items():
            section = f"=== {doc_type.upper()} ===\n\n"
            
            for i, doc in enumerate(docs):
                if doc_type == "metrics_history":
                    # Format spécifique pour les métriques
                    section += f"[Métrique {i+1}] {doc.get('content', '')}\n\n"
                elif doc_type == "hypothesis_result":
                    # Format spécifique pour les hypothèses
                    section += f"[Hypothèse {i+1}] {doc.get('content', '')}\n\n"
                else:
                    # Format standard pour les documents textuels
                    section += f"[Document {i+1}] {doc.get('content', '')}\n\n"
            
            formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def _build_enhanced_prompt(self, query: str, context: str) -> str:
        """
        Construit un prompt enrichi pour la génération de réponse.
        
        Args:
            query: Texte de la requête
            context: Contexte formaté
            
        Returns:
            Prompt complet
        """
        return f"""Contexte enrichi:
{context}

Question: {query}

En te basant sur le contexte enrichi fourni, réponds de manière précise et détaillée à la question.
Si le contexte contient des métriques ou des hypothèses, utilise-les pour étayer ta réponse.
Si différentes sources d'information sont disponibles, synthétise-les pour offrir une réponse complète.
Si le contexte ne contient pas suffisamment d'informations, indique-le clairement."""
    
    async def _generate_completion(self, prompt: str) -> str:
        """
        Génère une complétion avec le modèle de langage.
        
        Args:
            prompt: Prompt complet
            
        Returns:
            Réponse générée
        """
        response = await self.retry_manager.execute(
            lambda: self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800  # Augmentation pour des réponses plus complètes
            )
        )
        return response.choices[0].message.content
    
    def _generate_context_tags(self, context_documents: List[Dict[str, Any]]) -> List[str]:
        """
        Génère des tags pour la mise en cache intelligente.
        
        Args:
            context_documents: Documents de contexte utilisés
            
        Returns:
            Liste de tags
        """
        tags = [f"date:{datetime.now().strftime('%Y-%m-%d')}", "type:enhanced_rag"]
        
        # Ajout de tags basés sur les types de documents
        doc_types = set()
        node_ids = set()
        sources = set()
        
        for doc in context_documents:
            # Type de document
            doc_type = doc.get("metadata", {}).get("type", "document")
            doc_types.add(doc_type)
            
            # ID de nœud
            node_id = doc.get("node_id")
            if node_id:
                node_ids.add(f"node:{node_id[:8]}")  # Version tronquée pour éviter trop de tags
            
            # Source
            source = doc.get("metadata", {}).get("source")
            if source:
                sources.add(f"source:{source}")
        
        # Ajout des tags générés
        tags.extend([f"doctype:{t}" for t in doc_types])
        tags.extend(list(node_ids)[:5])  # Limite pour éviter l'explosion de tags
        tags.extend(list(sources))
        
        return tags
    
    async def _update_stats_for_cache_hit(self):
        """Met à jour les statistiques pour un cache hit"""
        stats = await self.mongo_ops.get_system_stats()
        if stats:
            total_queries = stats.get('total_queries', 0) + 1
            cache_hits = stats.get('cache_hits', 0) + 1
            await self.mongo_ops.update_system_stats({
                'total_queries': total_queries,
                'cache_hits': cache_hits,
                'cache_hit_rate': cache_hits / total_queries
            })
    
    async def _save_query_history(self, query_text: str, context_docs: List[Dict[str, Any]], start_time: datetime):
        """
        Enregistre l'historique de la requête et met à jour les statistiques.
        
        Args:
            query_text: Texte de la requête
            context_docs: Documents de contexte utilisés
            start_time: Heure de début du traitement
        """
        # Enregistrement de l'historique des requêtes avec métadonnées enrichies
        query_history = {
            "query": query_text,
            "timestamp": datetime.now(),
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "num_results": len(context_docs),
            "context_types": list(set(doc.get("metadata", {}).get("type", "document") for doc in context_docs)),
            "enhanced": True
        }
        await self.mongo_ops.save_query_history(query_history)
        
        # Mise à jour des statistiques
        stats = await self.mongo_ops.get_system_stats()
        if stats:
            total_queries = stats.get('total_queries', 0) + 1
            avg_time = stats.get('average_processing_time', 0)
            new_avg_time = ((avg_time * (total_queries - 1)) + 
                         (datetime.now() - start_time).total_seconds()) / total_queries
            
            await self.mongo_ops.update_system_stats({
                'total_queries': total_queries,
                'average_processing_time': new_avg_time,
                'last_query': datetime.now(),
                'enhanced_queries': stats.get('enhanced_queries', 0) + 1
            }) 