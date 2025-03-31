import asyncio
import logging
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetryConfig:
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,),
        fallback_value: Any = None
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions
        self.fallback_value = fallback_value

class RetryManager:
    def __init__(self):
        self.retry_stats: Dict[str, Dict[str, int]] = {}
        self.fallback_stats: Dict[str, Dict[str, int]] = {}

    def get_retry_stats(self, endpoint: str) -> Dict[str, int]:
        """Récupère les statistiques de retry pour un endpoint."""
        return self.retry_stats.get(endpoint, {"total": 0, "successful": 0, "failed": 0})

    def get_fallback_stats(self, endpoint: str) -> Dict[str, int]:
        """Récupère les statistiques de fallback pour un endpoint."""
        return self.fallback_stats.get(endpoint, {"total": 0, "successful": 0, "failed": 0})

    def update_retry_stats(self, endpoint: str, success: bool):
        """Met à jour les statistiques de retry."""
        if endpoint not in self.retry_stats:
            self.retry_stats[endpoint] = {"total": 0, "successful": 0, "failed": 0}
        
        stats = self.retry_stats[endpoint]
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

    def update_fallback_stats(self, endpoint: str, success: bool):
        """Met à jour les statistiques de fallback."""
        if endpoint not in self.fallback_stats:
            self.fallback_stats[endpoint] = {"total": 0, "successful": 0, "failed": 0}
        
        stats = self.fallback_stats[endpoint]
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

    def with_retry(self, config: RetryConfig, endpoint: str):
        """Décorateur pour appliquer la logique de retry."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Supprime les arguments args et kwargs s'ils existent
                if 'args' in kwargs:
                    del kwargs['args']
                if 'kwargs' in kwargs:
                    del kwargs['kwargs']
                return await self._retry_with_config(func, config, endpoint, *args, **kwargs)
            return wrapper
        return decorator

    def with_fallback(self, fallback_func, endpoint: str):
        """Décorateur pour appliquer la logique de fallback."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Supprime les arguments args et kwargs s'ils existent
                if 'args' in kwargs:
                    del kwargs['args']
                if 'kwargs' in kwargs:
                    del kwargs['kwargs']
                return await self._with_fallback(func, fallback_func, endpoint, *args, **kwargs)
            return wrapper
        return decorator

    async def _retry_with_config(self, func, config, endpoint, *args, **kwargs):
        last_exception = None
        delay = config.initial_delay

        for attempt in range(config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.update_retry_stats(endpoint, True)
                    logger.info(
                        f"Retry successful for {endpoint} after {attempt} attempts"
                    )
                return result

            except config.exceptions as e:
                last_exception = e
                if attempt < config.max_retries:
                    self.update_retry_stats(endpoint, False)
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries} failed for {endpoint}: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * config.backoff_factor, config.max_delay)
                else:
                    logger.error(
                        f"All retry attempts failed for {endpoint}: {str(e)}"
                    )
                    if config.fallback_value is not None:
                        self.update_fallback_stats(endpoint, True)
                        logger.info(f"Using fallback value for {endpoint}")
                        return config.fallback_value
                    raise last_exception

    async def _with_fallback(self, func, fallback_func, endpoint, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Primary function failed for {endpoint}, using fallback: {str(e)}"
            )
            try:
                result = await fallback_func(*args, **kwargs)
                self.update_fallback_stats(endpoint, True)
                return result
            except Exception as fallback_error:
                self.update_fallback_stats(endpoint, False)
                logger.error(
                    f"Fallback also failed for {endpoint}: {str(fallback_error)}"
                )
                raise fallback_error

# Instance globale du RetryManager
retry_manager = RetryManager() 