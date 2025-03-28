import os
import json
from typing import Any, Optional, Callable
import aioredis
from datetime import datetime, timedelta

class CacheManager:
    """Gestionnaire de cache utilisant Redis."""
    
    def __init__(self):
        # Utilisation des variables d'environnement Heroku pour Redis
        redis_url = os.getenv('REDIS_TLS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        
    async def get(self, key: str) -> Optional[str]:
        """Récupère une valeur du cache."""
        return await self.redis.get(key)
        
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Stocke une valeur dans le cache."""
        return await self.redis.set(key, value, ex=expire)
        
    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache."""
        return bool(await self.redis.delete(key))
        
    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe dans le cache."""
        return bool(await self.redis.exists(key))
        
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
        await self.redis.close() 