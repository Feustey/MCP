import asyncio
import random
from typing import Callable, TypeVar, Optional, List, Type
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RetryConfig:
    def __init__(
        self, 
        max_retries: int = 3, 
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        exceptions_to_retry: Optional[List[Type[Exception]]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions_to_retry = exceptions_to_retry or [Exception]

class RetryManager:
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.logger = logger

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Exécute une fonction avec une stratégie de retry avancée incluant backoff exponentiel.
        
        Args:
            func: La fonction à exécuter
            *args, **kwargs: Les arguments de la fonction
            
        Returns:
            Le résultat de la fonction
            
        Raises:
            Exception: Lève l'exception originale après tous les retries
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Vérifier si cette exception doit être retryée
                should_retry = any(isinstance(e, exc_type) for exc_type in self.config.exceptions_to_retry)
                if not should_retry:
                    self.logger.warning(f"Exception non-retryable rencontrée: {type(e).__name__}: {str(e)}")
                    raise e
                
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"Échec après {self.config.max_retries} tentatives. Dernière erreur: {str(e)}")
                    raise e
                
                # Calculer le délai de backoff exponentiel
                delay = min(
                    self.config.base_delay * (self.config.backoff_factor ** attempt),
                    self.config.max_delay
                )
                
                # Ajouter du jitter (variation aléatoire) si configuré
                if self.config.jitter:
                    delay = delay * (0.5 + random.random())
                
                self.logger.info(f"Tentative {attempt+1}/{self.config.max_retries} échouée: {str(e)}. Retry dans {delay:.2f}s")
                await asyncio.sleep(delay)
        
        # Ce code ne devrait jamais être atteint, mais au cas où
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Erreur inattendue dans le mécanisme de retry") 