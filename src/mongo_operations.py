from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.database import get_database, close_mongo_connection
from src.models import Document, QueryHistory, SystemStats, NodeData, ChannelData, NetworkMetrics, NodePerformance, ChannelRecommendation
from config import MONGO_URL, MONGO_DB_NAME

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoOperations:
    """Classe pour gérer les opérations MongoDB"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        
    async def connect(self):
        """Établit la connexion à MongoDB"""
        try:
            if not self.connected:
                self.client = MongoClient(MONGO_URL)
                self.db = self.client[MONGO_DB_NAME]
                # Vérification de la connexion
                self.client.admin.command('ping')
                self.connected = True
                logger.info("Connexion à MongoDB établie avec succès")
        except ConnectionFailure as e:
            logger.error(f"Erreur de connexion à MongoDB: {str(e)}")
            raise
            
    async def disconnect(self):
        """Ferme la connexion à MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Connexion à MongoDB fermée")
            
    async def ensure_connected(self):
        """S'assure que la connexion est établie"""
        if not self.connected:
            await self.connect()
            
    async def store_node_data(self, node_data: Dict[str, Any]):
        """Stocke les données d'un nœud"""
        await self.ensure_connected()
        try:
            node_data["last_update"] = datetime.now()
            result = self.db.nodes.update_one(
                {"node_id": node_data["node_id"]},
                {"$set": node_data},
                upsert=True
            )
            logger.info(f"Données du nœud {node_data['node_id']} stockées avec succès")
            return result
        except Exception as e:
            logger.error(f"Erreur lors du stockage des données du nœud: {str(e)}")
            raise
            
    async def get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les données d'un nœud"""
        await self.ensure_connected()
        try:
            node = self.db.nodes.find_one({"node_id": node_id})
            return node
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données du nœud: {str(e)}")
            return None
            
    async def store_analysis_result(self, node_id: str, analysis: Dict[str, Any]):
        """Stocke les résultats d'analyse"""
        await self.ensure_connected()
        try:
            analysis["timestamp"] = datetime.now()
            analysis["node_id"] = node_id
            result = self.db.analyses.insert_one(analysis)
            logger.info(f"Analyse du nœud {node_id} stockée avec succès")
            return result
        except Exception as e:
            logger.error(f"Erreur lors du stockage de l'analyse: {str(e)}")
            raise
            
    async def get_latest_analysis(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Récupère la dernière analyse d'un nœud"""
        await self.ensure_connected()
        try:
            analysis = self.db.analyses.find_one(
                {"node_id": node_id},
                sort=[("timestamp", -1)]
            )
            return analysis
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'analyse: {str(e)}")
            return None
            
    async def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Récupère tous les nœuds"""
        await self.ensure_connected()
        try:
            nodes = list(self.db.nodes.find())
            return nodes
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des nœuds: {str(e)}")
            return []

    async def save_document(self, document: Document) -> str:
        """Sauvegarde un document dans MongoDB"""
        if self.db is None:
            await self.connect()
        doc_dict = document.model_dump()
        result = await self.db.documents.insert_one(doc_dict)
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Récupère un document par son ID"""
        if self.db is None:
            await self.connect()
        doc_dict = await self.db.documents.find_one({"_id": doc_id})
        if doc_dict:
            return Document(**doc_dict)
        return None

    async def save_query_history(self, query_history: QueryHistory) -> str:
        """Sauvegarde l'historique d'une requête"""
        if self.db is None:
            await self.connect()
        query_dict = query_history.model_dump()
        result = await self.db.query_history.insert_one(query_dict)
        return str(result.inserted_id)

    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Récupère les requêtes récentes"""
        if self.db is None:
            await self.connect()
        cursor = self.db.query_history.find().sort("created_at", -1).limit(limit)
        queries = await cursor.to_list(length=limit)
        return [QueryHistory(**q) for q in queries]

    async def update_system_stats(self, stats: SystemStats) -> None:
        """Met à jour les statistiques du système"""
        if self.db is None:
            await self.connect()
        stats_dict = stats.model_dump()
        await self.db.system_stats.update_one(
            {},
            {"$set": stats_dict},
            upsert=True
        )

    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère les statistiques du système"""
        if self.db is None:
            await self.connect()
        stats_dict = await self.db.system_stats.find_one()
        if stats_dict:
            return SystemStats(**stats_dict)
        return None

    async def get_documents_by_source(self, source: str) -> List[Document]:
        """Récupère tous les documents d'une source"""
        if self.db is None:
            await self.connect()
        cursor = self.db.documents.find({"source": source})
        docs = await cursor.to_list(length=None)
        return [Document(**doc) for doc in docs]

    async def get_all_documents(self) -> List[Document]:
        """Récupère tous les documents RAG (pour reindex)."""
        if self.db is None:
            await self.connect()
        cursor = self.db.documents.find({})
        docs = await cursor.to_list(length=None)
        out = []
        for doc in docs:
            doc = dict(doc)
            if "_id" in doc:
                doc["id"] = str(doc.pop("_id"))
            out.append(Document(**doc))
        return out

    # Nouvelles méthodes pour la gestion des nœuds et canaux
    async def save_node(self, node: NodeData) -> str:
        """Sauvegarde ou met à jour un nœud"""
        if self.db is None:
            await self.connect()
        node_dict = node.model_dump()
        result = self.db.nodes.update_one(
            {"node_id": node.node_id},
            {"$set": node_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else node.node_id

    async def save_channel(self, channel: ChannelData) -> str:
        """Sauvegarde ou met à jour un canal"""
        if self.db is None:
            await self.connect()
        channel_dict = channel.model_dump()
        result = self.db.channels.update_one(
            {"channel_id": channel.channel_id},
            {"$set": channel_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else channel.channel_id

    async def save_network_metrics(self, metrics: NetworkMetrics) -> None:
        """Sauvegarde ou met à jour les métriques réseau"""
        if self.db is None:
            await self.connect()
        metrics_dict = metrics.model_dump()
        await self.db.network_metrics.update_one(
            {},
            {"$set": metrics_dict},
            upsert=True
        )

    async def save_node_performance(self, performance: NodePerformance) -> str:
        """Sauvegarde ou met à jour les performances d'un nœud"""
        if self.db is None:
            await self.connect()
        perf_dict = performance.model_dump()
        result = await self.db.node_performance.update_one(
            {"node_id": performance.node_id},
            {"$set": perf_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else performance.node_id

    async def save_channel_recommendation(self, recommendation: ChannelRecommendation) -> str:
        """Sauvegarde ou met à jour une recommandation de canal"""
        if self.db is None:
            await self.connect()
        rec_dict = recommendation.model_dump()
        result = await self.db.channel_recommendations.update_one(
            {
                "source_node_id": recommendation.source_node_id,
                "target_node_id": recommendation.target_node_id
            },
            {"$set": rec_dict},
            upsert=True
        )
        return str(result.upserted_id) if result.upserted_id else f"{recommendation.source_node_id}_{recommendation.target_node_id}" 