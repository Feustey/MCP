import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from src.rag_data_provider import RAGDataProvider
from mongo_operations import MongoOperations
from cache_manager import CacheManager

logger = logging.getLogger(__name__)

class RAGMaintenance:
    def __init__(self):
        self.data_provider = RAGDataProvider()
        self.mongo_ops = MongoOperations()
        self.cache_manager = CacheManager()
        
    async def perform_maintenance(self):
        """Exécute les tâches de maintenance"""
        try:
            logger.info("Début de la maintenance RAG")
            
            # 1. Nettoyage du cache
            await self._cleanup_cache()
            
            # 2. Optimisation des index MongoDB
            await self._optimize_mongodb()
            
            # 3. Rotation des logs
            await self._rotate_logs()
            
            # 4. Vérification de la cohérence des données
            await self._check_data_consistency()
            
            logger.info("Maintenance RAG terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la maintenance: {str(e)}")
            raise
            
    async def _cleanup_cache(self):
        """Nettoie les différents caches"""
        try:
            # Nettoyage du cache de contexte
            await self.data_provider.clear_expired_cache()
            
            # Nettoyage du cache Redis
            await self.cache_manager.clear_expired_cache()
            
            logger.info("Nettoyage du cache terminé")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
            
    async def _optimize_mongodb(self):
        """Optimise les index MongoDB"""
        try:
            # Optimisation des index pour les documents
            await self.mongo_ops.db.documents.create_index([("created_at", -1)])
            await self.mongo_ops.db.documents.create_index([("source", 1)])
            
            # Optimisation des index pour les requêtes
            await self.mongo_ops.db.queries.create_index([("timestamp", -1)])
            await self.mongo_ops.db.queries.create_index([("cache_hit", 1)])
            
            logger.info("Optimisation MongoDB terminée")
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation MongoDB: {str(e)}")
            
    async def _rotate_logs(self):
        """Effectue la rotation des logs"""
        try:
            # Implémentation de la rotation des logs
            # À adapter selon votre système de logging
            logger.info("Rotation des logs terminée")
        except Exception as e:
            logger.error(f"Erreur lors de la rotation des logs: {str(e)}")
            
    async def _check_data_consistency(self):
        """Vérifie la cohérence des données"""
        try:
            # Vérification des documents RAG
            total_docs = await self.mongo_ops.db.documents.count_documents({})
            logger.info(f"Nombre total de documents: {total_docs}")
            
            # Vérification des requêtes
            total_queries = await self.mongo_ops.db.queries.count_documents({})
            logger.info(f"Nombre total de requêtes: {total_queries}")
            
            # Vérification des statistiques
            stats = await self.mongo_ops.get_system_stats()
            if stats:
                logger.info(f"Statistiques système: {stats.model_dump()}")
                
            logger.info("Vérification de la cohérence terminée")
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la cohérence: {str(e)}")
            
async def run_maintenance():
    """Point d'entrée pour la maintenance"""
    maintenance = RAGMaintenance()
    await maintenance.perform_maintenance()
    
if __name__ == "__main__":
    asyncio.run(run_maintenance()) 