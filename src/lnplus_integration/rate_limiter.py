from datetime import datetime, timedelta
from typing import Dict, List
import asyncio

class AdaptiveRateLimiter:
    def __init__(
        self,
        default_rate: int = 60,  # requêtes par minute
        high_priority_rate: int = 120,
        window_size: int = 60  # taille de la fenêtre en secondes
    ):
        self.rate_limits = {
            "default": default_rate,
            "high_priority": high_priority_rate
        }
        self.window_size = window_size
        self.requests: Dict[str, List[datetime]] = {}
        self._lock = asyncio.Lock()

    async def should_throttle(self, priority: str = "default") -> bool:
        """Détermine si une requête doit être limitée"""
        async with self._lock:
            current_time = datetime.now()
            window_start = current_time - timedelta(seconds=self.window_size)
            
            # Nettoyer les requêtes anciennes
            if priority in self.requests:
                self.requests[priority] = [
                    req_time for req_time in self.requests[priority]
                    if req_time > window_start
                ]
            else:
                self.requests[priority] = []
            
            # Vérifier le taux actuel
            current_rate = len(self.requests[priority])
            if current_rate >= self.rate_limits[priority]:
                return True
                
            # Enregistrer la nouvelle requête
            self.requests[priority].append(current_time)
            return False

    def adjust_rate_limit(self, priority: str, new_limit: int):
        """Ajuste dynamiquement la limite de taux"""
        if priority in self.rate_limits:
            self.rate_limits[priority] = new_limit

    def get_current_rate(self, priority: str) -> int:
        """Retourne le taux actuel pour une priorité donnée"""
        if priority in self.requests:
            current_time = datetime.now()
            window_start = current_time - timedelta(seconds=self.window_size)
            return len([
                req_time for req_time in self.requests[priority]
                if req_time > window_start
            ])
        return 0

# Instance singleton
rate_limiter = AdaptiveRateLimiter() 