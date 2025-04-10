from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from models import Document, QueryHistory, SystemStats, NodeData, NodePerformance, SecurityMetrics, Recommendation
import os
from datetime import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoOperations:
    def __init__(self):
        # URL de connexion MongoDB
        mongo_url = os.getenv("DATABASE_URL", "mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng")
        logger.info(f"Tentative de connexion à MongoDB avec l'URL: {mongo_url}")
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client.get_database("dazlng")  # Utilisation de la base dazlng
        logger.info("Connexion MongoDB établie avec succès")
        
    async def save_document(self, document: Document) -> bool:
        try:
            result = await self.db.documents.insert_one(document.model_dump())
            return bool(result.inserted_id)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du document: {str(e)}")
            return False
            
    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        try:
            cursor = self.db.queries.find().sort("timestamp", -1).limit(limit)
            queries = await cursor.to_list(length=limit)
            return [QueryHistory(**query) for query in queries]
        except Exception as e:
            print(f"Erreur lors de la récupération des requêtes: {str(e)}")
            return []
            
    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère ou initialise les statistiques du système"""
        try:
            stats = await self.db.stats.find_one()
            if not stats:
                # Initialisation des statistiques si elles n'existent pas
                stats = {
                    "total_documents": 0,
                    "total_queries": 0,
                    "average_processing_time": 0.0,
                    "cache_hit_rate": 0.0,
                    "last_updated": datetime.now()
                }
                await self.db.stats.insert_one(stats)
            return SystemStats(**stats)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return None
            
    async def update_system_stats(self, stats: SystemStats) -> bool:
        """Met à jour les statistiques du système"""
        try:
            stats_dict = stats.model_dump()
            result = await self.db.stats.replace_one(
                {},
                stats_dict,
                upsert=True
            )
            return bool(result.modified_count or result.upserted_id)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques: {str(e)}")
            return False

    async def get_node_data(self, node_id: str) -> Optional[NodeData]:
        """Récupère les données d'un nœud spécifique"""
        try:
            node = await self.db.nodes.find_one({"node_id": node_id})
            return NodeData(**node) if node else None
        except Exception as e:
            print(f"Erreur lors de la récupération des données du nœud: {str(e)}")
            return None

    async def get_node_performance(self, node_id: str) -> Optional[NodePerformance]:
        """Récupère les données de performance d'un nœud"""
        try:
            perf = await self.db.node_performance.find_one({"node_id": node_id})
            return NodePerformance(**perf) if perf else None
        except Exception as e:
            print(f"Erreur lors de la récupération des performances du nœud: {str(e)}")
            return None

    async def get_security_metrics(self, node_id: str) -> Optional[SecurityMetrics]:
        """Récupère les métriques de sécurité d'un nœud"""
        try:
            metrics = await self.db.security_metrics.find_one({"node_id": node_id})
            return SecurityMetrics(**metrics) if metrics else None
        except Exception as e:
            print(f"Erreur lors de la récupération des métriques de sécurité: {str(e)}")
            return None

    async def save_recommendation(self, recommendation: Recommendation) -> bool:
        """Sauvegarde une recommandation dans la base de données"""
        try:
            result = await self.db.recommendations.insert_one(recommendation.model_dump())
            return bool(result.inserted_id)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la recommandation: {str(e)}")
            return False

    async def get_node_recommendations(self, node_id: str, limit: int = 10) -> List[Recommendation]:
        """Récupère les recommandations pour un nœud spécifique"""
        try:
            cursor = self.db.recommendations.find(
                {"node_id": node_id, "status": "active"}
            ).sort("created_at", -1).limit(limit)
            recommendations = await cursor.to_list(length=limit)
            return [Recommendation(**rec) for rec in recommendations]
        except Exception as e:
            print(f"Erreur lors de la récupération des recommandations: {str(e)}")
            return []

    async def save_query_history(self, query_history: QueryHistory) -> bool:
        """Sauvegarde l'historique d'une requête"""
        try:
            result = await self.db.query_history.insert_one(query_history.model_dump())
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de l'historique de requête: {str(e)}")
            return False 