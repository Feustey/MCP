import redis
import os
import json
from typing import Any, Optional, Callable
from datetime import timedelta
import logging

class CacheManager:
    """Gestionnaire de cache amélioré utilisant Redis."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )
        
        # Configuration des TTLs par type de données
        self.cache_ttls = {
            'node_data': timedelta(hours=1),
            'network_metrics': timedelta(minutes=30),
            'channel_data': timedelta(hours=2),
            'wallet_data': timedelta(minutes=15)
        }
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        
    async def get(self, key: str, data_type: str = 'default') -> Optional[Any]:
        """Récupère une valeur du cache avec gestion des erreurs améliorée."""
        try:
            cached = self.redis_client.get(f"{data_type}:{key}")
            if cached:
                return json.loads(cached)
            return None
        except redis.RedisError as e:
            self.logger.error(f"Erreur Redis lors de la récupération de {key}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de décodage JSON pour {key}: {str(e)}")
            return None
        
    async def set(self, key: str, value: Any, data_type: str = 'default') -> bool:
        """Stocke une valeur dans le cache avec TTL approprié."""
        try:
            ttl = self.cache_ttls.get(data_type, timedelta(hours=1))
            return self.redis_client.setex(
                f"{data_type}:{key}",
                ttl,
                json.dumps(value)
            )
        except redis.RedisError as e:
            self.logger.error(f"Erreur Redis lors de la mise en cache de {key}: {str(e)}")
            return False
        except (TypeError, ValueError) as e:
            self.logger.error(f"Erreur de sérialisation pour {key}: {str(e)}")
            return False
        
    async def delete(self, key: str, data_type: str = 'default') -> bool:
        """Supprime une valeur du cache."""
        try:
            return bool(self.redis_client.delete(f"{data_type}:{key}"))
        except redis.RedisError as e:
            self.logger.error(f"Erreur Redis lors de la suppression de {key}: {str(e)}")
            return False
        
    async def exists(self, key: str, data_type: str = 'default') -> bool:
        """Vérifie si une clé existe dans le cache."""
        try:
            return bool(self.redis_client.exists(f"{data_type}:{key}"))
        except redis.RedisError as e:
            self.logger.error(f"Erreur Redis lors de la vérification de {key}: {str(e)}")
            return False
        
    async def get_or_set(self, key: str, getter: Callable, data_type: str = 'default') -> Any:
        """Récupère une valeur du cache ou l'obtient via la fonction getter."""
        cached = await self.get(key, data_type)
        if cached is not None:
            return cached
            
        value = await getter()
        await self.set(key, value, data_type)
        return value
        
    def get_key(self, *args) -> str:
        """Génère une clé de cache à partir des arguments."""
        return ':'.join(str(arg) for arg in args)
        
    async def cleanup(self):
        """Ferme la connexion Redis."""
        try:
            await self.redis_client.close()
        except redis.RedisError as e:
            self.logger.error(f"Erreur lors de la fermeture de Redis: {str(e)}")
        
    async def clear_pattern(self, pattern: str) -> bool:
        """Supprime toutes les clés correspondant à un motif."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except redis.RedisError as e:
            self.logger.error(f"Erreur Redis lors du nettoyage du pattern {pattern}: {str(e)}")
            return False 