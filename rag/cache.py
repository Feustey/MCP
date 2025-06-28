import redis.asyncio as redis
from functools import wraps
import json
import logging
from typing import Any, Optional
from config.rag_config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache."""
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Stocke une valeur dans le cache."""
        try:
            ttl = ttl or settings.CACHE_TTL
            await self.redis.set(
                key,
                json.dumps(value),
                ex=ttl
            )
            return True
        except Exception as e:
            logger.error(f"Erreur lors du stockage dans le cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache: {e}")
            return False

def cache_key_generator(*args, **kwargs) -> str:
    """Génère une clé de cache unique basée sur les arguments."""
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)

def cached(ttl: Optional[int] = None):
    """Décorateur pour mettre en cache les résultats des fonctions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = RedisCache()
            key = f"{func.__name__}:{cache_key_generator(*args, **kwargs)}"
            
            # Essayer de récupérer du cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit pour {key}")
                return cached_value
            
            # Exécuter la fonction si pas en cache
            result = await func(*args, **kwargs)
            
            # Mettre en cache le résultat
            await cache.set(key, result, ttl)
            logger.debug(f"Cache miss pour {key}, valeur mise en cache")
            
            return result
        return wrapper
    return decorator

# Instance globale du cache
cache = RedisCache() 