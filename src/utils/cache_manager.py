"""
Gestionnaire de cache Redis pour MCP
Version adaptée de mcp-light avec fonctionnalités étendues
"""

import redis.asyncio as redis
import json
import os
import logging
from typing import Any, Optional, Dict, List
import pickle
import hashlib
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger("mcp.cache")

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = int(os.getenv("CACHE_TTL", 300))  # 5 minutes par défaut
        self.namespace = os.getenv("CACHE_NAMESPACE", "mcp")
        self._redis = None
        self._connection_pool = None
        
        # Configuration des TTL par type de données
        self.ttl_config = {
            "node_info": 300,      # 5 minutes
            "recommendations": 600, # 10 minutes
            "network_summary": 900, # 15 minutes
            "fee_analysis": 180,   # 3 minutes
            "openai_response": 1800, # 30 minutes
            "sparkseer_data": 240  # 4 minutes
        }
    
    async def _get_redis(self):
        """Obtient une connexion Redis avec pool de connexions"""
        if self._redis is None:
            try:
                # Configuration du pool de connexions
                if self._connection_pool is None:
                    self._connection_pool = redis.ConnectionPool.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        max_connections=20,
                        retry_on_timeout=True
                    )
                
                self._redis = redis.Redis(connection_pool=self._connection_pool)
                
                # Test de connexion
                await self._redis.ping()
                logger.info(f"Connexion Redis établie sur {self.redis_url}")
                
            except Exception as e:
                logger.warning(f"Connexion Redis échouée: {str(e)}")
                self._redis = None
                
        return self._redis
    
    def _make_key(self, key: str, data_type: str = None) -> str:
        """Génère une clé Redis avec namespace et type"""
        if data_type:
            return f"{self.namespace}:{data_type}:{key}"
        return f"{self.namespace}:{key}"
    
    def _hash_complex_key(self, key_parts: Dict[str, Any]) -> str:
        """Génère une clé hashée pour des structures complexes"""
        key_string = json.dumps(key_parts, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get(self, key: str, data_type: str = None) -> Optional[Any]:
        """Récupère une valeur du cache"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return None
            
            cache_key = self._make_key(key, data_type)
            value = await redis_client.get(cache_key)
            
            if value:
                try:
                    # Tentative de désérialisation JSON d'abord
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Fallback vers pickle pour les objets complexes
                    try:
                        return pickle.loads(value.encode('latin1'))
                    except:
                        return value
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache pour {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, data_type: str = None) -> bool:
        """Stocke une valeur dans le cache"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            
            # Déterminer le TTL approprié
            if ttl is None:
                ttl = self.ttl_config.get(data_type, self.default_ttl)
            
            cache_key = self._make_key(key, data_type)
            
            # Sérialisation intelligente
            try:
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                # Fallback vers pickle pour les objets non-JSON
                serialized_value = pickle.dumps(value).decode('latin1')
            
            await redis_client.setex(cache_key, ttl, serialized_value)
            logger.debug(f"Cache mis à jour: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage en cache pour {key}: {str(e)}")
            return False
    
    async def get_or_set(self, key: str, fetch_func, ttl: Optional[int] = None, data_type: str = None) -> Any:
        """Pattern get-or-set: récupère du cache ou exécute la fonction"""
        cached_value = await self.get(key, data_type)
        
        if cached_value is not None:
            logger.debug(f"Cache hit pour {key}")
            return cached_value
        
        logger.debug(f"Cache miss pour {key}, exécution de la fonction")
        value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
        
        if value is not None:
            await self.set(key, value, ttl, data_type)
        
        return value
    
    async def delete(self, key: str, data_type: str = None) -> bool:
        """Supprime une valeur du cache"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            
            cache_key = self._make_key(key, data_type)
            result = await redis_client.delete(cache_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache pour {key}: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str, data_type: str = None) -> int:
        """Supprime toutes les clés correspondant au pattern"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return 0
            
            search_pattern = self._make_key(pattern, data_type)
            keys = await redis_client.keys(search_pattern)
            
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Suppression de {deleted} clés correspondant à {search_pattern}")
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression par pattern {pattern}: {str(e)}")
            return 0
    
    async def exists(self, key: str, data_type: str = None) -> bool:
        """Vérifie si une clé existe dans le cache"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            
            cache_key = self._make_key(key, data_type)
            return await redis_client.exists(cache_key) > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'existence pour {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str, data_type: str = None) -> int:
        """Retourne le TTL restant d'une clé (-1 si permanente, -2 si inexistante)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return -2
            
            cache_key = self._make_key(key, data_type)
            return await redis_client.ttl(cache_key)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du TTL pour {key}: {str(e)}")
            return -2
    
    async def increment(self, key: str, amount: int = 1, data_type: str = None) -> Optional[int]:
        """Incrémente une valeur numérique"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return None
            
            cache_key = self._make_key(key, data_type)
            return await redis_client.incrby(cache_key, amount)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'incrémentation pour {key}: {str(e)}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques du cache"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return {"error": "Redis non disponible"}
            
            info = await redis_client.info()
            
            # Compter les clés par namespace
            namespace_pattern = f"{self.namespace}:*"
            keys = await redis_client.keys(namespace_pattern)
            
            stats = {
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                },
                "mcp_cache": {
                    "total_keys": len(keys),
                    "namespace": self.namespace,
                    "default_ttl": self.default_ttl
                }
            }
            
            # Calculer le hit ratio
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            if hits + misses > 0:
                stats["redis_info"]["hit_ratio"] = hits / (hits + misses)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {str(e)}")
            return {"error": str(e)}
    
    async def clear_all(self) -> bool:
        """Vide tout le cache du namespace MCP"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            
            pattern = f"{self.namespace}:*"
            deleted = await self.delete_pattern("*")
            logger.info(f"Cache MCP vidé: {deleted} clés supprimées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du vidage du cache: {str(e)}")
            return False
    
    async def close(self):
        """Ferme les connexions Redis"""
        try:
            if self._redis:
                await self._redis.close()
            if self._connection_pool:
                await self._connection_pool.disconnect()
            logger.info("Connexions Redis fermées")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture des connexions: {str(e)}")

# Instance globale du cache manager
cache_manager = CacheManager() 