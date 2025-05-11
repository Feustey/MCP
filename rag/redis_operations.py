import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import redis.asyncio as redis
import logging
from rag.models import Document, QueryHistory, SystemStats

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisOperations:
    """Classe pour gérer les opérations Redis"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self.ttl = 3600  # TTL par défaut en secondes
        
    async def _init_redis(self):
        """Initialise la connexion Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url)
            
    async def _close_redis(self):
        """Ferme la connexion Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            
    async def cache_document(self, doc: Document) -> bool:
        """Met en cache un document"""
        try:
            await self._init_redis()
            key = f"doc:{doc.source}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(doc.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache du document: {str(e)}")
            return False
            
    async def get_cached_document(self, source: str) -> Optional[Document]:
        """Récupère un document du cache"""
        try:
            await self._init_redis()
            key = f"doc:{source}"
            data = await self.redis.get(key)
            if data:
                return Document(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du document: {str(e)}")
            return None
            
    async def cache_query_history(self, query: QueryHistory) -> bool:
        """Met en cache l'historique d'une requête"""
        try:
            await self._init_redis()
            key = f"query:{query.timestamp.timestamp()}"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(query.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache de la requête: {str(e)}")
            return False
            
    async def get_recent_queries(self, limit: int = 10) -> List[QueryHistory]:
        """Récupère les requêtes récentes"""
        try:
            await self._init_redis()
            keys = await self.redis.keys("query:*")
            queries = []
            for key in sorted(keys, reverse=True)[:limit]:
                data = await self.redis.get(key)
                if data:
                    queries.append(QueryHistory(**json.loads(data)))
            return queries
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des requêtes: {str(e)}")
            return []
            
    async def update_system_stats(self, stats: SystemStats) -> bool:
        """Met à jour les statistiques système"""
        try:
            await self._init_redis()
            key = "system:stats"
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(stats.dict())
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des stats: {str(e)}")
            return False
            
    async def get_system_stats(self) -> Optional[SystemStats]:
        """Récupère les statistiques système"""
        try:
            await self._init_redis()
            key = "system:stats"
            data = await self.redis.get(key)
            if data:
                return SystemStats(**json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {str(e)}")
            return None 