"""
Redis caching service for MCP Lightning system.
Provides intelligent caching for Lightning node analysis and AI-powered insights.
"""

import json
import redis
import asyncio
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RedisCacheService:
    """
    Intelligent caching service with TTL management and AI analysis caching.
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.use_mock = os.getenv("REDIS_USE_MOCK", "false").lower() == "true"
        
        if self.use_mock or not self.redis_url:
            logger.warning("Redis cache en mode mock - pas de cache persistant")
            self.client = None
            self.mock_cache = {}
        else:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                self.client.ping()
                logger.info("Redis cache connecté avec succès")
            except Exception as e:
                logger.error(f"Erreur connexion Redis: {str(e)}, basculement mode mock")
                self.client = None
                self.mock_cache = {}
    
    def _generate_cache_key(self, prefix: str, identifier: str, params: Optional[Dict] = None) -> str:
        """Generate a unique cache key."""
        key_data = f"{prefix}:{identifier}"
        if params:
            # Sort params for consistent hashing
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_data += f":{param_hash}"
        return key_data
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.client:
                value = await asyncio.to_thread(self.client.get, key)
                if value:
                    return json.loads(value)
            else:
                # Mock mode
                cache_entry = self.mock_cache.get(key)
                if cache_entry:
                    if datetime.now() < cache_entry['expires']:
                        return cache_entry['data']
                    else:
                        del self.mock_cache[key]
            return None
        except Exception as e:
            logger.error(f"Erreur lecture cache {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL."""
        try:
            if self.client:
                serialized = json.dumps(value, default=str)
                success = await asyncio.to_thread(self.client.setex, key, ttl_seconds, serialized)
                return bool(success)
            else:
                # Mock mode
                expires = datetime.now() + timedelta(seconds=ttl_seconds)
                self.mock_cache[key] = {
                    'data': value,
                    'expires': expires
                }
                return True
        except Exception as e:
            logger.error(f"Erreur écriture cache {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if self.client:
                success = await asyncio.to_thread(self.client.delete, key)
                return bool(success)
            else:
                # Mock mode
                if key in self.mock_cache:
                    del self.mock_cache[key]
                return True
        except Exception as e:
            logger.error(f"Erreur suppression cache {key}: {str(e)}")
            return False
    
    async def cache_lightning_analysis(self, node_id: str, analysis_data: Dict, ttl_hours: int = 6) -> bool:
        """Cache Lightning node analysis with appropriate TTL."""
        key = self._generate_cache_key("lightning_analysis", node_id)
        
        # Add cache metadata
        cached_data = {
            'node_id': node_id,
            'analysis': analysis_data,
            'cached_at': datetime.now().isoformat(),
            'cache_type': 'lightning_analysis'
        }
        
        return await self.set(key, cached_data, ttl_seconds=ttl_hours * 3600)
    
    async def get_lightning_analysis(self, node_id: str) -> Optional[Dict]:
        """Get cached Lightning node analysis."""
        key = self._generate_cache_key("lightning_analysis", node_id)
        cached_data = await self.get(key)
        
        if cached_data and isinstance(cached_data, dict):
            logger.info(f"Cache hit pour analyse Lightning: {node_id}")
            return cached_data.get('analysis')
        
        logger.debug(f"Cache miss pour analyse Lightning: {node_id}")
        return None
    
    async def cache_ai_insight(self, query_hash: str, insight_data: Dict, ttl_hours: int = 24) -> bool:
        """Cache AI-powered insights with longer TTL."""
        key = self._generate_cache_key("ai_insight", query_hash)
        
        cached_data = {
            'query_hash': query_hash,
            'insight': insight_data,
            'generated_at': datetime.now().isoformat(),
            'cache_type': 'ai_insight'
        }
        
        return await self.set(key, cached_data, ttl_seconds=ttl_hours * 3600)
    
    async def get_ai_insight(self, query_hash: str) -> Optional[Dict]:
        """Get cached AI insight."""
        key = self._generate_cache_key("ai_insight", query_hash)
        cached_data = await self.get(key)
        
        if cached_data and isinstance(cached_data, dict):
            logger.info(f"Cache hit pour insight IA: {query_hash[:8]}...")
            return cached_data.get('insight')
        
        return None
    
    async def cache_network_data(self, data_type: str, data: Dict, ttl_minutes: int = 30) -> bool:
        """Cache network data with shorter TTL for real-time data."""
        key = self._generate_cache_key("network", data_type)
        
        cached_data = {
            'type': data_type,
            'data': data,
            'updated_at': datetime.now().isoformat()
        }
        
        return await self.set(key, cached_data, ttl_seconds=ttl_minutes * 60)
    
    async def get_network_data(self, data_type: str) -> Optional[Dict]:
        """Get cached network data."""
        key = self._generate_cache_key("network", data_type)
        cached_data = await self.get(key)
        
        if cached_data and isinstance(cached_data, dict):
            return cached_data.get('data')
        
        return None
    
    async def generate_query_hash(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate a consistent hash for AI queries."""
        query_data = {
            'query': query.strip().lower(),
            'params': params or {}
        }
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.sha256(query_str.encode()).hexdigest()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'connected': self.client is not None,
            'mode': 'redis' if self.client else 'mock',
            'mock_entries': len(self.mock_cache) if not self.client else 0
        }
        
        if self.client:
            try:
                info = await asyncio.to_thread(self.client.info)
                stats.update({
                    'redis_version': info.get('redis_version', 'unknown'),
                    'used_memory': info.get('used_memory_human', 'unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'keys_count': await asyncio.to_thread(self.client.dbsize)
                })
            except Exception as e:
                logger.error(f"Erreur récupération stats Redis: {str(e)}")
                stats['error'] = str(e)
        
        return stats
    
    async def cleanup_expired_mock_cache(self):
        """Clean up expired entries in mock cache."""
        if not self.client and self.mock_cache:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.mock_cache.items()
                if now >= entry['expires']
            ]
            for key in expired_keys:
                del self.mock_cache[key]
            
            if expired_keys:
                logger.debug(f"Nettoyé {len(expired_keys)} entrées expirées du cache mock")

# Instance globale du service de cache
cache_service = RedisCacheService()