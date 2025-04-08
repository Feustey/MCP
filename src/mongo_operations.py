from datetime import datetime
from typing import List, Dict, Any, Optional
from .database import get_database, close_mongo_connection
from .models import Document, QueryHistory, SystemStats, NodeData, ChannelData, NetworkMetrics, NodePerformance, ChannelRecommendation

class MongoOperations:
    def __init__(self):
        self.db = None

    async def initialize(self):
        """Initialise la connexion à la base de données"""
        if self.db is None:
            self.db = await get_database()
        return self

    async def close(self):
        """Ferme la connexion à la base de données"""
        if self.db:
            await close_mongo_connection()
            self.db = None

    async def save_document(self, document: Dict[str, Any]) -> str:
        """Sauvegarde un document dans MongoDB"""
        if self.db is None:
            await self.initialize()
        result = await self.db.documents.insert_one(document)
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un document par son ID"""
        if self.db is None:
            await self.initialize()
        return await self.db.documents.find_one({"_id": doc_id})

    async def save_query_history(self, query_history: QueryHistory) -> str:
        """Sauvegarde l'historique d'une requête"""
        if self.db is None:
            await self.initialize()
        query_dict = query_history.model_dump()
        result = await self.db.query_history.insert_one(query_dict)
        return str(result.inserted_id)

    async def update_system_stats(self, stats: Dict[str, Any]) -> None:
        """Met à jour les statistiques du système"""
        if self.db is None:
            await self.initialize()
        await self.db.system_stats.update_one(
            {},
            {"$set": stats},
            upsert=True
        )

    async def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Récupère les statistiques du système"""
        if self.db is None:
            await self.initialize()
        return await self.db.system_stats.find_one()

    async def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les requêtes récentes"""
        if self.db is None:
            await self.initialize()
        cursor = self.db.query_history.find().sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_documents_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Récupère tous les documents d'une source"""
        if self.db is None:
            await self.initialize()
        cursor = self.db.documents.find({"source": source})
        return await cursor.to_list(length=None)

    # Nouvelles méthodes pour la gestion des nœuds et canaux
    async def save_node(self, node: NodeData) -> str:
        """Sauvegarde ou met à jour un nœud"""
        if self.db is None:
            await self.initialize()
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
            await self.initialize()
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
            await self.initialize()
        metrics_dict = metrics.model_dump()
        await self.db.network_metrics.update_one(
            {},
            {"$set": metrics_dict},
            upsert=True
        )

    async def save_node_performance(self, performance: NodePerformance) -> str:
        """Sauvegarde ou met à jour les performances d'un nœud"""
        if self.db is None:
            await self.initialize()
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
            await self.initialize()
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