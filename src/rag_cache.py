import redis
import json
from typing import Any, Optional
import aioredis

class RAGCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis = None
        self.host = host
        self.port = port
        self.db = db
        self._initialized = False

    async def initialize(self):
        """Initialise la connexion au cache"""
        if not self._initialized:
            self.redis = await aioredis.create_redis_pool(
                f'redis://{self.host}:{self.port}',
                db=self.db
            )
            self._initialized = True

    async def close(self):
        """Ferme la connexion au cache"""
        if self._initialized and self.redis:
            self.redis.close()
            await self.redis.wait_closed()
            self._initialized = False

    async def set(self, key: str, value: Any, data_type: str, ttl: int = 3600) -> bool:
        """Stocke une valeur dans le cache"""
        if not self._initialized:
            await self.initialize()
        try:
            serialized = json.dumps(value)
            await self.redis.set(f"{data_type}:{key}", serialized, expire=ttl)
            return True
        except Exception:
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        if not self._initialized:
            await self.initialize()
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache"""
        if not self._initialized:
            await self.initialize()
        return bool(await self.redis.delete(key))

    async def clear_pattern(self, pattern: str) -> int:
        """Supprime toutes les clés correspondant à un pattern"""
        if not self._initialized:
            await self.initialize()
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0 