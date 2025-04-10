import asyncio
import logging
import time
from enum import Enum
from typing import Callable, TypeVar, Any, Optional, Dict, List
import functools

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CircuitState(Enum):
    CLOSED = "closed"      # Circuit fermé (normal)
    OPEN = "open"          # Circuit ouvert (erreurs, pas de requêtes)
    HALF_OPEN = "half_open"  # Circuit mi-ouvert (période de test)


class CircuitBreakerConfig:
    def __init__(
        self,
        failure_threshold: int = 5,        # Nombre d'erreurs consécutives avant ouverture
        recovery_timeout: float = 30.0,    # Secondes avant de passer en half-open
        reset_timeout: float = 60.0,       # Secondes de succès en half-open avant fermeture
        execution_timeout: float = 30.0,   # Timeout d'exécution par défaut
        exclude_exceptions: Optional[List[Exception]] = None  # Exceptions qui ne déclenchent pas le circuit breaker
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.reset_timeout = reset_timeout
        self.execution_timeout = execution_timeout
        self.exclude_exceptions = exclude_exceptions or []


class CircuitBreaker:
    """
    Implémentation d'un circuit breaker pour protéger contre les défaillances des services externes.
    
    Le circuit breaker surveille les erreurs et, lorsqu'un seuil est atteint, ouvre le circuit
    pour éviter de surcharger un service défaillant. Après un délai, il permet quelques requêtes
    pour tester si le service est rétabli.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self.metrics = {
            "success_count": 0,
            "failure_count": 0,
            "rejected_count": 0,
            "timeout_count": 0,
        }
        self.logger = logger

    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Exécute une fonction en appliquant la logique du circuit breaker.
        
        Args:
            func: La fonction à exécuter
            *args, **kwargs: Les arguments de la fonction
            
        Returns:
            Le résultat de la fonction
            
        Raises:
            CircuitOpenError: Si le circuit est ouvert
            Exception: Pour toute autre erreur
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                self.logger.info(f"Circuit {self.name} passe de OPEN à HALF_OPEN après {self.config.recovery_timeout}s")
                self.state = CircuitState.HALF_OPEN
            else:
                self.metrics["rejected_count"] += 1
                self.logger.warning(f"Circuit {self.name} est OUVERT - requête rejetée")
                raise CircuitOpenError(f"Circuit {self.name} est ouvert")
        
        try:
            # Timeout pour éviter les requêtes qui bloquent trop longtemps
            start_time = time.time()
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.execution_timeout
            )
            execution_time = time.time() - start_time
            
            # Mise à jour des métriques de succès
            self.failure_count = 0
            self.last_success_time = time.time()
            self.metrics["success_count"] += 1
            
            # Si en half-open et succès pendant assez longtemps, revenir à closed
            if self.state == CircuitState.HALF_OPEN:
                if time.time() - self.last_success_time >= self.config.reset_timeout:
                    self.logger.info(f"Circuit {self.name} passe de HALF_OPEN à CLOSED après {self.config.reset_timeout}s de succès")
                    self.state = CircuitState.CLOSED
            
            self.logger.debug(f"Exécution réussie via {self.name} en {execution_time:.2f}s (état: {self.state.value})")
            return result
            
        except asyncio.TimeoutError:
            self.metrics["timeout_count"] += 1
            self._handle_failure("timeout")
            raise
            
        except Exception as e:
            # Vérifier si l'exception est exclue du circuit breaker
            if any(isinstance(e, exc_type) for exc_type in self.config.exclude_exceptions):
                self.logger.debug(f"Exception exclue du circuit breaker {self.name}: {type(e).__name__}")
                raise
                
            self.metrics["failure_count"] += 1
            self._handle_failure(str(e))
            raise
            
    def _handle_failure(self, reason: str):
        """Gestion de l'échec d'une requête avec mise à jour de l'état du circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.logger.warning(f"Circuit {self.name} passe de CLOSED à OPEN après {self.failure_count} échecs")
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            self.logger.warning(f"Échec en état HALF_OPEN, circuit {self.name} repasse à OPEN")
            self.state = CircuitState.OPEN
            
        self.logger.error(f"Échec d'exécution via {self.name}: {reason} (état: {self.state.value})")
            
    def get_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques du circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "metrics": self.metrics,
            "last_failure": self.last_failure_time,
            "last_success": self.last_success_time
        }
        
    def reset(self):
        """Réinitialise le circuit breaker à l'état fermé"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.logger.info(f"Circuit {self.name} réinitialisé à l'état CLOSED")


class CircuitOpenError(Exception):
    """Exception levée lorsque le circuit est ouvert"""
    pass


# Décorateur pour faciliter l'utilisation
def circuit_protected(circuit_name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Décorateur pour protéger une fonction avec un circuit breaker.
    
    Usage:
        @circuit_protected("external_api")
        async def call_external_api():
            ...
    """
    circuit = CircuitBreaker(circuit_name, config)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit.execute(func, *args, **kwargs)
        return wrapper
    return decorator


# Gestionnaire central pour tous les circuit breakers
class CircuitBreakerRegistry:
    """Registre central pour tous les circuit breakers de l'application"""
    
    _instances: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get(cls, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Récupère ou crée un circuit breaker par son nom"""
        if name not in cls._instances:
            cls._instances[name] = CircuitBreaker(name, config)
        return cls._instances[name]
        
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """Récupère les métriques de tous les circuit breakers"""
        return {name: cb.get_metrics() for name, cb in cls._instances.items()}
        
    @classmethod
    def reset_all(cls):
        """Réinitialise tous les circuit breakers"""
        for cb in cls._instances.values():
            cb.reset() 