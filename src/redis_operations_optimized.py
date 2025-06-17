"""
Module optimisé pour les opérations Redis
Dernière mise à jour: 7 mai 2025
"""

import redis
from redis import Redis
from typing import Optional, Any, Dict
import structlog
from config import Settings

logger = structlog.get_logger(__name__)

def get_redis_client() -> Redis:
    """
    Crée et retourne un client Redis optimisé avec la configuration actuelle
    """
    settings = Settings()
    redis_config = settings.redis
    
    try:
        client = Redis(
            host=redis_config.host,
            port=redis_config.port,
            username=redis_config.username,
            password=redis_config.password,
            ssl=redis_config.ssl,
            decode_responses=True,
            socket_timeout=redis_config.socket_timeout,
            socket_connect_timeout=redis_config.socket_connect_timeout,
            retry_on_timeout=redis_config.retry_on_timeout,
            health_check_interval=redis_config.health_check_interval,
            max_connections=redis_config.max_connections
        )
        
        # Test de connexion
        client.ping()
        logger.info("Connexion Redis établie avec succès", 
                   host=redis_config.host,
                   port=redis_config.port)
        return client
        
    except redis.ConnectionError as e:
        logger.error("Erreur de connexion Redis",
                    error=str(e),
                    host=redis_config.host,
                    port=redis_config.port)
        raise

def get_redis_pool() -> redis.ConnectionPool:
    """
    Crée et retourne un pool de connexions Redis optimisé
    """
    settings = Settings()
    redis_config = settings.redis
    
    return redis.ConnectionPool(
        host=redis_config.host,
        port=redis_config.port,
        username=redis_config.username,
        password=redis_config.password,
        ssl=redis_config.ssl,
        decode_responses=True,
        socket_timeout=redis_config.socket_timeout,
        socket_connect_timeout=redis_config.socket_connect_timeout,
        max_connections=redis_config.max_connections
    )

# Pool de connexions global
REDIS_POOL = get_redis_pool()

def get_redis_from_pool() -> Redis:
    """
    Retourne un client Redis utilisant le pool de connexions global
    """
    return Redis(connection_pool=REDIS_POOL)

class RedisCache:
    """
    Classe utilitaire pour la gestion du cache Redis
    """
    def __init__(self, client: Optional[Redis] = None):
        self.client = client or get_redis_from_pool()
    
    def get(self, key: str) -> Optional[str]:
        """Récupère une valeur du cache"""
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.error("Erreur lors de la récupération Redis", 
                        error=str(e), key=key)
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Stocke une valeur dans le cache
        :param ttl: Durée de vie en secondes
        """
        try:
            return bool(self.client.set(key, value, ex=ttl))
        except redis.RedisError as e:
            logger.error("Erreur lors du stockage Redis",
                        error=str(e), key=key)
            return False
    
    def delete(self, key: str) -> bool:
        """Supprime une clé du cache"""
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.error("Erreur lors de la suppression Redis",
                        error=str(e), key=key)
            return False
    
    def exists(self, key: str) -> bool:
        """Vérifie si une clé existe"""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.error("Erreur lors de la vérification Redis",
                        error=str(e), key=key)
            return False 