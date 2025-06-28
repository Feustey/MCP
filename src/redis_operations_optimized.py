"""
Module optimisé pour les opérations Redis
Dernière mise à jour: 7 mai 2025
"""

import redis
from redis import Redis
from typing import Optional, Any, Dict
import structlog
from config import settings

logger = structlog.get_logger(__name__)

def get_redis_client() -> Redis:
    """
    Crée et retourne un client Redis optimisé avec la configuration actuelle
    """
    try:
        client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            username=settings.redis_username,
            password=settings.redis_password,
            ssl=settings.redis_ssl,
            decode_responses=True,
            socket_timeout=5.0, # Valeur raisonnable
            socket_connect_timeout=5.0, # Valeur raisonnable
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=20
        )
        
        # Test de connexion
        client.ping()
        logger.info("Connexion Redis établie avec succès", 
                   host=settings.redis_host,
                   port=settings.redis_port)
        return client
        
    except redis.ConnectionError as e:
        logger.error("Erreur de connexion Redis",
                    error=str(e),
                    host=settings.redis_host,
                    port=settings.redis_port)
        raise

def get_redis_pool() -> redis.ConnectionPool:
    """
    Crée et retourne un pool de connexions Redis optimisé
    """
    return redis.ConnectionPool(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
        ssl=settings.redis_ssl,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        max_connections=20
    )

# Pool de connexions global
# Note: La création du pool est différée jusqu'à ce qu'elle soit nécessaire
# pour éviter les erreurs au démarrage si Redis n'est pas encore prêt.
_REDIS_POOL = None

def get_redis_from_pool() -> Redis:
    """
    Retourne un client Redis utilisant le pool de connexions global (lazy-loaded)
    """
    global _REDIS_POOL
    if _REDIS_POOL is None:
        _REDIS_POOL = get_redis_pool()
    return Redis(connection_pool=_REDIS_POOL)

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

class RedisOperations:
    """
    Classe pour les opérations Redis avec méthodes de santé
    """
    def __init__(self):
        self.client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifie la santé de Redis"""
        try:
            if self.client is None:
                self.client = get_redis_client()
            
            # Test de ping
            self.client.ping()
            
            # Test de base
            test_key = "health_check_test"
            self.client.set(test_key, "ok", ex=10)
            result = self.client.get(test_key)
            self.client.delete(test_key)
            
            if result == "ok":
                return {
                    "status": "healthy",
                    "ping": "ok",
                    "write": "ok",
                    "read": "ok"
                }
            else:
                return {
                    "status": "degraded",
                    "ping": "ok",
                    "write": "error",
                    "read": "error"
                }
                
        except Exception as e:
            logger.error("Erreur health check Redis", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Instance globale pour l'import
redis_ops = RedisOperations() 