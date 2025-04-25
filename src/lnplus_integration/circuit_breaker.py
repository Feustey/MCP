from datetime import datetime, timedelta
import asyncio
from typing import Callable, Any
from .exceptions import LNPlusNetworkError

class LNPlusCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failure_count = 0
        self.last_failure = None
        self.state = "closed"  # closed, open, half-open
        self.last_state_change = datetime.now()

    def _should_retry(self) -> bool:
        """Détermine si une requête doit être réessayée"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            if (datetime.now() - self.last_state_change).seconds > self.reset_timeout:
                self.state = "half-open"
                self.last_state_change = datetime.now()
                return True
            return False
            
        if self.state == "half-open":
            if (datetime.now() - self.last_state_change).seconds > self.half_open_timeout:
                self.state = "closed"
                self.failure_count = 0
                return True
            return False

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction avec le circuit breaker"""
        if not self._should_retry():
            raise LNPlusNetworkError("Circuit breaker ouvert")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                self.last_state_change = datetime.now()
                
            raise LNPlusNetworkError(f"Erreur réseau: {str(e)}")

    def reset(self):
        """Réinitialise le circuit breaker"""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure = None
        self.last_state_change = datetime.now()

# Instance singleton
circuit_breaker = LNPlusCircuitBreaker() 