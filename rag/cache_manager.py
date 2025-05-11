import redis
import os
import json
from typing import Any, Optional, Callable

class CacheManager:
    """Gestionnaire de cache utilisant Redis."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )
        
    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache."""
        try:
            return self.redis_client.get(key)
        except Exception:
            return None
        
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Stocke une valeur dans le cache."""
        try:
            return self.redis_client.set(key, value, ex=expire)
        except Exception:
            return False
        
    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception:
            return False
        
    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache."""
        return bool(self.redis_client.exists(key))
        
    async def get_or_set(self, key: str, getter: Callable, expire: Optional[int] = 3600) -> Any:
        """Récupère une valeur du cache ou l'obtient via la fonction getter."""
        cached = await self.get(key)
        if cached is not None:
            return json.loads(cached)
            
        value = await getter()
        await self.set(key, json.dumps(value), expire)
        return value
        
    def get_key(self, *args) -> str:
        """Génère une clé de cache à partir des arguments."""
        return ':'.join(str(arg) for arg in args)
        
    async def cleanup(self):
        """Ferme la connexion Redis."""
        await self.redis_client.close()
        
    async def clear_pattern(self, pattern: str) -> bool:
        """Supprime toutes les clés correspondant à un motif."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except Exception:
            return False 