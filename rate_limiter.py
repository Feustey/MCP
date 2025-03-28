import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cache_manager import CacheManager

class RateLimiter:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.limiter = Limiter(key_func=get_remote_address)
        
        # Configuration des limites (requêtes par minute)
        self.rate_limits = {
            'default': 60,  # 60 requêtes par minute
            'optimize_node': 30,  # 30 requêtes par minute
            'sparkseer_data': 100,  # 100 requêtes par minute
            'health': 300,  # 300 requêtes par minute
        }
        
        # Configuration des quotas quotidiens
        self.daily_quotas = {
            'default': 1000,  # 1000 requêtes par jour
            'optimize_node': 500,  # 500 requêtes par jour
            'sparkseer_data': 2000,  # 2000 requêtes par jour
        }
        
        # Configuration des timeouts (en secondes)
        self.timeouts = {
            'network_summary': 10,
            'centralities': 10,
            'node_stats': 5,
            'node_history': 5,
            'channel_recommendations': 5,
            'liquidity_value': 5,
            'suggested_fees': 5,
            'bid_info': 5,
        }

    def get_rate_limit(self, endpoint: str) -> int:
        """Récupère la limite de taux pour un endpoint spécifique."""
        return self.rate_limits.get(endpoint, self.rate_limits['default'])

    def get_daily_quota(self, endpoint: str) -> int:
        """Récupère le quota quotidien pour un endpoint spécifique."""
        return self.daily_quotas.get(endpoint, self.daily_quotas['default'])

    def get_timeout(self, endpoint: str) -> int:
        """Récupère le timeout pour un endpoint spécifique."""
        return self.timeouts.get(endpoint, 10)  # 10 secondes par défaut

    async def check_rate_limit(self, request: Request, endpoint: str) -> bool:
        """Vérifie si la requête respecte les limites de taux."""
        try:
            # Vérification du rate limit par minute
            rate_limit = self.get_rate_limit(endpoint)
            key = f"rate_limit:{endpoint}:{get_remote_address(request)}"
            
            current = await self.cache.get(key)
            if current is None:
                await self.cache.set(key, 1, 60)  # 60 secondes
                return True
            
            if current >= rate_limit:
                raise RateLimitExceeded(f"Rate limit exceeded for {endpoint}")
            
            await self.cache.set(key, current + 1, 60)
            
            # Vérification du quota quotidien
            daily_key = f"daily_quota:{endpoint}:{get_remote_address(request)}"
            daily_count = await self.cache.get(daily_key)
            
            if daily_count is None:
                await self.cache.set(daily_key, 1, 86400)  # 24 heures
                return True
            
            daily_quota = self.get_daily_quota(endpoint)
            if daily_count >= daily_quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily quota exceeded for {endpoint}"
                )
            
            await self.cache.set(daily_key, daily_count + 1, 86400)
            return True
            
        except Exception as e:
            if isinstance(e, (RateLimitExceeded, HTTPException)):
                raise e
            print(f"Erreur lors de la vérification du rate limit: {str(e)}")
            return True  # En cas d'erreur, on autorise la requête

    def rate_limit(self, endpoint: str):
        """Décorateur pour appliquer le rate limiting à un endpoint."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                request = kwargs.get('request')
                if request:
                    await self.check_rate_limit(request, endpoint)
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    async def clear_limits(self, ip: str):
        """Réinitialise toutes les limites pour une IP."""
        patterns = [
            f"rate_limit:*:{ip}",
            f"daily_quota:*:{ip}"
        ]
        for pattern in patterns:
            await self.cache.clear_pattern(pattern) 