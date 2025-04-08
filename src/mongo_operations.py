from datetime import datetime
from typing import List, Dict, Any, Optional
from .database import get_database, close_mongo_connection
from .models import Document, QueryHistory, SystemStats, NodeData, ChannelData, NetworkMetrics, NodePerformance, ChannelRecommendation

class MongoOperations:
    def __init__(self):
        self.db = None

    async def connect(self):
        """Établit la connexion à la base de données"""
        if self.db is None:
            self.db = await get_database()
        return self

    async def initialize(self):
        """Initialise la connexion à la base de données"""
        return await self.connect()

    async def close(self):
        """Ferme la connexion à la base de données"""
        if self.db:
            await close_mongo_connection()
            self.db = None

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

    # Nouvelles méthodes pour la gestion des nœuds et canaux
    async def save_node(self, node: NodeData) -> str:
        """Sauvegarde ou met à jour un nœud"""
        if self.db is None:
            await self.connect()
        node_dict = node.model_dump()
        result = await self.db.nodes.update_one(
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
        result = await self.db.channels.update_one(
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