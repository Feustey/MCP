from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from models import Document, QueryHistory, SystemStats, NodeData, NodePerformance, SecurityMetrics, Recommendation
import os
from datetime import datetime
import logging
import json

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
            
    # Nouvelles méthodes pour les données de réseau
    async def save_network_summary(self, network_summary: Dict[str, Any]) -> bool:
        """Sauvegarde les données de résumé temporel du réseau"""
        try:
            # Ajout d'un timestamp pour tracer l'historique des données
            network_summary['timestamp'] = datetime.now()
            
            # Sauvegarder dans une collection spécifique aux résumés réseau
            result = await self.db.network_summaries.insert_one(network_summary)
            
            # Mettre à jour le "dernier" résumé dans une collection séparée pour accès rapide
            await self.db.latest_data.update_one(
                {"data_type": "network_summary"},
                {"$set": {"data": network_summary, "updated_at": datetime.now()}},
                upsert=True
            )
            
            logger.info(f"Résumé réseau sauvegardé avec succès, ID: {result.inserted_id}")
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du résumé réseau: {str(e)}")
            return False

    async def get_latest_network_summary(self) -> Optional[Dict[str, Any]]:
        """Récupère le dernier résumé réseau sauvegardé"""
        try:
            result = await self.db.latest_data.find_one({"data_type": "network_summary"})
            if result and 'data' in result:
                return result['data']
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé réseau: {str(e)}")
            return None

    async def save_centralities(self, centralities: Dict[str, Any]) -> bool:
        """Sauvegarde les données de centralités du réseau"""
        try:
            # Ajout d'un timestamp
            centralities['timestamp'] = datetime.now()
            
            # Sauvegarder dans une collection pour les centralités
            result = await self.db.centralities.insert_one(centralities)
            
            # Mettre à jour les "dernières" centralités dans une collection pour accès rapide
            await self.db.latest_data.update_one(
                {"data_type": "centralities"},
                {"$set": {"data": centralities, "updated_at": datetime.now()}},
                upsert=True
            )
            
            logger.info(f"Centralités sauvegardées avec succès, ID: {result.inserted_id}")
            return bool(result.inserted_id)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des centralités: {str(e)}")
            return False

    async def get_latest_centralities(self) -> Optional[Dict[str, Any]]:
        """Récupère les dernières centralités sauvegardées"""
        try:
            result = await self.db.latest_data.find_one({"data_type": "centralities"})
            if result and 'data' in result:
                return result['data']
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des centralités: {str(e)}")
            return None
            
    async def save_json_to_collection(self, json_file_path: str, collection_name: str) -> bool:
        """Charge un fichier JSON et sauvegarde son contenu dans une collection MongoDB"""
        try:
            # Vérifier que le fichier existe
            if not os.path.exists(json_file_path):
                logger.error(f"Le fichier {json_file_path} n'existe pas.")
                return False
                
            # Charger les données JSON
            with open(json_file_path, 'r') as f:
                data = json.load(f)
                
            # Si les données sont un dictionnaire, le convertir en liste pour insertion
            if isinstance(data, dict):
                # Ajouter un timestamp
                data['timestamp'] = datetime.now()
                documents = [data]
            elif isinstance(data, list):
                # Ajouter un timestamp à chaque élément
                for item in data:
                    if isinstance(item, dict):
                        item['timestamp'] = datetime.now()
                documents = data
            else:
                logger.error(f"Format de données non supporté dans {json_file_path}")
                return False
                
            # Effectuer l'insertion
            result = await self.db[collection_name].insert_many(documents)
            
            logger.info(f"Données de {json_file_path} importées avec succès vers la collection {collection_name}. {len(result.inserted_ids)} documents insérés.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'importation des données de {json_file_path}: {str(e)}")
            return False 