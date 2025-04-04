from datetime import datetime
from typing import List, Dict, Any, Optional
from .database import get_database, close_mongo_connection
from .models import Document, QueryHistory, SystemStats

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

    async def save_document(self, document: Document) -> str:
        """Sauvegarde un document dans MongoDB"""
        if self.db is None:
            await self.initialize()
        doc_dict = document.model_dump()
        result = await self.db.documents.insert_one(doc_dict)
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Récupère un document par son ID"""
        if self.db is None:
            await self.initialize()
        doc = await self.db.documents.find_one({"_id": doc_id})
        return Document(**doc) if doc else None

    async def save_query_history(self, query_history: QueryHistory) -> str:
        """Sauvegarde l'historique d'une requête"""
        if self.db is None:
            await self.initialize()
        query_dict = query_history.model_dump()
        result = await self.db.query_history.insert_one(query_dict)
        return str(result.inserted_id)

    async def update_system_stats(self, stats: SystemStats) -> None:
        """Met à jour les statistiques du système"""
        if self.db is None:
            await self.initialize()
        stats_dict = stats.model_dump()
        await self.db.system_stats.update_one(
            {},
            {"$set": stats_dict},
            upsert=True
        )

    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère les statistiques du système"""
        if self.db is None:
            await self.initialize()
        stats = await self.db.system_stats.find_one()
        return SystemStats(**stats) if stats else None

    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Récupère les requêtes récentes"""
        if self.db is None:
            await self.initialize()
        cursor = self.db.query_history.find().sort("created_at", -1).limit(limit)
        queries = await cursor.to_list(length=limit)
        return [QueryHistory(**query) for query in queries]

    async def get_documents_by_source(self, source: str) -> List[Document]:
        """Récupère tous les documents d'une source"""
        if self.db is None:
            await self.initialize()
        cursor = self.db.documents.find({"source": source})
        docs = await cursor.to_list(length=None)
        return [Document(**doc) for doc in docs] 