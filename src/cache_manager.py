import logging
from typing import Dict, Any, Optional
import asyncio
import time

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        self.cache_ttls = {
            "embedding": 24 * 3600,  # 24 heures
            "response": 3600,        # 1 heure
            "context": 4 * 3600      # 4 heures
        }
        self.redis_client = None
        self.logger = logger

    async def initialize(self, redis_client=None):
        """Initialise le cache manager avec un client Redis optionnel"""
        self.redis_client = redis_client
        return self

    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache si elle existe et n'est pas expirée"""
        if key in self.cache and not self._is_expired(key):
            return self.cache.get(key)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Stocke une valeur dans le cache avec un timestamp"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
        
        # Utilisation du TTL spécifique ou du TTL par défaut selon le préfixe de la clé
        if ttl is None:
            prefix = key.split(':')[0] if ':' in key else "default"
            ttl = self.cache_ttls.get(prefix, 3600)  # par défaut 1 heure

    async def delete(self, key: str) -> bool:
        """Supprime une entrée du cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.timestamps:
                del self.timestamps[key]
            return True
        return False

    async def clear_expired_cache(self):
        """Nettoie les entrées de cache expirées"""
        try:
            # Nettoyage du cache en mémoire
            current_time = time.time()
            expired_keys = []
            
            for key, timestamp in self.timestamps.items():
                prefix = key.split(':')[0] if ':' in key else "default"
                ttl = self.cache_ttls.get(prefix, 3600)
                
                if current_time - timestamp > ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                await self.delete(key)
                
            self.logger.info(f"Nettoyage du cache: {len(expired_keys)} entrées supprimées")
            
            # Nettoyage du cache Redis si disponible
            if self.redis_client:
                pipeline = self.redis_client.pipeline()
                for key_pattern in self.cache_ttls.keys():
                    expired_keys = await self.redis_client.keys(f"{key_pattern}:*")
                    if expired_keys:
                        await pipeline.delete(*expired_keys)
                await pipeline.execute()
                self.logger.info("Nettoyage du cache Redis terminé")
                
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage du cache: {str(e)}")
            return False
            
    def _is_expired(self, key: str) -> bool:
        """Vérifie si une entrée du cache a expiré"""
        if key not in self.timestamps:
            return True
            
        current_time = time.time()
        timestamp = self.timestamps[key]
        prefix = key.split(':')[0] if ':' in key else "default"
        ttl = self.cache_ttls.get(prefix, 3600)
        
        return current_time - timestamp > ttl 