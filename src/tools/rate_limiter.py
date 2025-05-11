from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from rag.cache_manager import CacheManager

# Création d'une instance globale du rate limiter
limiter = Limiter(key_func=get_remote_address)

class RateLimiter:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.limiter = limiter
        
    async def check_rate_limit(self, request: Request) -> bool:
        """Vérifie si la requête respecte les limites de taux."""
        try:
            await self.limiter.check_rate_limit(request)
            return True
        except Exception:
            return False

def get_limiter():
    """Retourne l'instance globale du rate limiter."""
    return limiter 