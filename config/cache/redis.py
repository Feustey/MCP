"""
Configuration du cache Redis
Gestion du cache et des sessions pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import logging
from typing import Optional, Dict, Any, Union
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
import json
from datetime import datetime, timedelta

# Configuration du logging
logger = logging.getLogger("mcp.cache")

# Variables d'environnement
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_SSL = os.getenv("REDIS_SSL", "true").lower() == "true"
REDIS_SSL_CERT_REQS = os.getenv("REDIS_SSL_CERT_REQS", "required")

# Configuration du cache
CACHE_PREFIX = "mcp:"
DEFAULT_TTL = 3600  # 1 heure
SESSION_TTL = 86400  # 24 heures
RATE_LIMIT_TTL = 60  # 1 minute

class RedisCache:
    """Gestionnaire de cache Redis"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        
    async def connect(self) -> bool:
        """Établit la connexion à Redis"""
        try:
            # Options de connexion
            options = {
                "host": REDIS_HOST,
                "port": REDIS_PORT,
                "db": REDIS_DB,
                "ssl": REDIS_SSL,
                "ssl_cert_reqs": REDIS_SSL_CERT_REQS,
                "decode_responses": True
            }
            
            if REDIS_PASSWORD:
                options["password"] = REDIS_PASSWORD
            
            # Connexion
            self.client = redis.Redis(**options)
            
            # Test de connexion
            await self.client.ping()
            logger.info("Connected to Redis successfully")
            return True
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {str(e)}")
            return False
    
    async def disconnect(self):
        """Ferme la connexion à Redis"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Redis")
    
    def _get_key(self, key: str) -> str:
        """Préfixe une clé avec le préfixe du cache"""
        return f"{CACHE_PREFIX}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        try:
            value = await self.client.get(self._get_key(key))
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get value from Redis: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Stocke une valeur dans le cache"""
        try:
            await self.client.setex(
                self._get_key(key),
                ttl,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set value in Redis: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Supprime une valeur du cache"""
        try:
            await self.client.delete(self._get_key(key))
            return True
        except Exception as e:
            logger.error(f"Failed to delete value from Redis: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Vérifie si une clé existe"""
        try:
            return await self.client.exists(self._get_key(key))
        except Exception as e:
            logger.error(f"Failed to check key existence in Redis: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Incrémente une valeur"""
        try:
            return await self.client.incrby(self._get_key(key), amount)
        except Exception as e:
            logger.error(f"Failed to increment value in Redis: {str(e)}")
            return None
    
    async def set_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Stocke une session"""
        return await self.set(f"session:{session_id}", data, SESSION_TTL)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une session"""
        return await self.get(f"session:{session_id}")
    
    async def delete_session(self, session_id: str) -> bool:
        """Supprime une session"""
        return await self.delete(f"session:{session_id}")
    
    async def check_rate_limit(self, key: str, limit: int) -> bool:
        """Vérifie le rate limiting"""
        try:
            current = await self.increment(key)
            if current is None:
                return False
                
            if current == 1:
                await self.client.expire(self._get_key(key), RATE_LIMIT_TTL)
                
            return current <= limit
            
        except Exception as e:
            logger.error(f"Failed to check rate limit in Redis: {str(e)}")
            return False
    
    async def check_health(self) -> Dict[str, Any]:
        """Vérifie la santé du cache"""
        try:
            # Vérifier la connexion
            await self.client.ping()
            
            # Vérifier les statistiques
            info = await self.client.info()
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "total_connections_received": info.get("total_connections_received", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }

# Instance globale
redis_cache = RedisCache()

# Fonctions utilitaires
async def get_cache():
    """Récupère l'instance du cache"""
    if not redis_cache.client:
        await redis_cache.connect()
    return redis_cache

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Récupère une session"""
    cache = await get_cache()
    return await cache.get_session(session_id)

async def set_session(session_id: str, data: Dict[str, Any]) -> bool:
    """Stocke une session"""
    cache = await get_cache()
    return await cache.set_session(session_id, data)

async def delete_session(session_id: str) -> bool:
    """Supprime une session"""
    cache = await get_cache()
    return await cache.delete_session(session_id)

async def check_rate_limit(key: str, limit: int) -> bool:
    """Vérifie le rate limiting"""
    cache = await get_cache()
    return await cache.check_rate_limit(key, limit) 