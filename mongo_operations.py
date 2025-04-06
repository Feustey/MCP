from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from models import Document, QueryHistory, SystemStats
import os
from datetime import datetime

class MongoOperations:
    def __init__(self):
        self.client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
        self.db = self.client.lnbits
        
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
        try:
            stats = await self.db.stats.find_one()
            return SystemStats(**stats) if stats else None
        except Exception as e:
            print(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return None
            
    async def update_system_stats(self, stats: dict) -> bool:
        try:
            result = await self.db.stats.replace_one(
                {},
                stats,
                upsert=True
            )
            return bool(result.modified_count or result.upserted_id)
        except Exception as e:
            print(f"Erreur lors de la mise à jour des statistiques: {str(e)}")
            return False 