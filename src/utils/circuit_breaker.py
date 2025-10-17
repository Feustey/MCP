"""
Circuit Breaker Pattern pour protéger les services externes
Évite les cascades de failures et améliore la résilience
"""

import asyncio
import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict
from functools import wraps
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """États possibles du circuit breaker"""
    CLOSED = "closed"          # Normal - requêtes passent
    OPEN = "open"              # Failing - rejeter les requêtes
    HALF_OPEN = "half_open"    # Testing - tester la récupération


@dataclass
class CircuitBreakerStats:
    """Statistiques du circuit breaker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: list = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calcule le taux de succès"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire pour export"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rejected_requests': self.rejected_requests,
            'success_rate': self.success_rate(),
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'state_changes_count': len(self.state_changes)
        }


class CircuitBreakerOpenError(Exception):
    """Exception levée quand le circuit est ouvert"""
    def __init__(self, service_name: str, stats: Optional[Dict] = None):
        self.service_name = service_name
        self.stats = stats
        message = f"Circuit breaker is OPEN for service '{service_name}' - service temporarily unavailable"
        if stats:
            message += f". Success rate: {stats.get('success_rate', 0):.2%}"
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit Breaker pour protéger les appels aux services externes
    
    États:
    - CLOSED: Normal, toutes les requêtes passent
    - OPEN: Service défaillant, rejeter les requêtes
    - HALF_OPEN: Test de récupération, laisser passer quelques requêtes
    
    Paramètres:
    - failure_threshold: Nombre d'échecs avant d'ouvrir le circuit
    - recovery_timeout: Temps avant de tenter une récupération (secondes)
    - success_threshold: Nombre de succès nécessaires pour refermer le circuit
    - expected_exception: Type d'exception à considérer comme échec
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        expected_exception: type = Exception,
        half_open_max_requests: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        self.half_open_max_requests = half_open_max_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_requests = 0
        self.stats = CircuitBreakerStats()
        
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s, "
            f"success_threshold={success_threshold}"
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute une fonction à travers le circuit breaker
        
        Args:
            func: Fonction asynchrone à exécuter
            *args, **kwargs: Arguments de la fonction
            
        Returns:
            Résultat de la fonction
            
        Raises:
            CircuitBreakerOpenError: Si le circuit est ouvert
            Exception: Si la fonction échoue
        """
        async with self._lock:
            self.stats.total_requests += 1
            
            # Vérifier l'état du circuit
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}': Tentative de récupération (HALF_OPEN)")
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self.stats.rejected_requests += 1
                    logger.warning(
                        f"Circuit breaker '{self.name}' is OPEN - "
                        f"rejecting request (failures: {self.failure_count}/{self.failure_threshold})"
                    )
                    raise CircuitBreakerOpenError(self.name, self.stats.to_dict())
            
            # En mode HALF_OPEN, limiter le nombre de requêtes de test
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_requests >= self.half_open_max_requests:
                    self.stats.rejected_requests += 1
                    raise CircuitBreakerOpenError(
                        self.name,
                        {"reason": "max half-open requests reached"}
                    )
                self.half_open_requests += 1
        
        # Exécuter la fonction
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except self.expected_exception as e:
            await self._on_failure(e)
            raise
    
    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Version synchrone de call() pour compatibilité"""
        return asyncio.run(self.call(func, *args, **kwargs))
    
    async def _on_success(self):
        """Appelé après un succès"""
        async with self._lock:
            self.stats.successful_requests += 1
            self.stats.last_success_time = datetime.now()
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.info(
                    f"Circuit breaker '{self.name}': Success in HALF_OPEN "
                    f"({self.success_count}/{self.success_threshold})"
                )
                
                if self.success_count >= self.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}': Récupération réussie, fermeture du circuit")
                    self._transition_to(CircuitState.CLOSED)
                    self.success_count = 0
                    self.half_open_requests = 0
    
    async def _on_failure(self, exception: Exception):
        """Appelé après un échec"""
        async with self._lock:
            self.stats.failed_requests += 1
            self.stats.last_failure_time = datetime.now()
            self.failure_count += 1
            
            logger.warning(
                f"Circuit breaker '{self.name}': Failure detected "
                f"({self.failure_count}/{self.failure_threshold}) - {type(exception).__name__}: {str(exception)}"
            )
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}': Failure in HALF_OPEN, reopening circuit")
                self._transition_to(CircuitState.OPEN)
                self.success_count = 0
                self.half_open_requests = 0
            
            elif self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}': Failure threshold reached "
                    f"({self.failure_count} failures), opening circuit"
                )
                self._transition_to(CircuitState.OPEN)
    
    def _should_attempt_reset(self) -> bool:
        """Détermine si on doit tenter une récupération"""
        if not self.stats.last_failure_time:
            return False
        
        elapsed = datetime.now() - self.stats.last_failure_time
        return elapsed > timedelta(seconds=self.recovery_timeout)
    
    def _transition_to(self, new_state: CircuitState):
        """Transition vers un nouvel état"""
        old_state = self.state
        self.state = new_state
        
        self.stats.state_changes.append({
            'from': old_state.value,
            'to': new_state.value,
            'timestamp': datetime.now().isoformat(),
            'failure_count': self.failure_count,
            'success_count': self.success_count
        })
        
        logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}")
    
    def get_state(self) -> CircuitState:
        """Retourne l'état actuel"""
        return self.state
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            **self.stats.to_dict()
        }
    
    def reset(self):
        """Réinitialise le circuit breaker"""
        logger.info(f"Circuit breaker '{self.name}': Manual reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_requests = 0
        # Garder les stats pour historique
    
    def force_open(self):
        """Force l'ouverture du circuit (pour maintenance)"""
        logger.warning(f"Circuit breaker '{self.name}': Forced OPEN")
        self._transition_to(CircuitState.OPEN)


# ============================================================================
# DÉCORATEUR POUR CIRCUIT BREAKER
# ============================================================================

def with_circuit_breaker(
    breaker: CircuitBreaker,
    fallback: Optional[Callable] = None
):
    """
    Décorateur pour protéger une fonction avec un circuit breaker
    
    Args:
        breaker: Instance de CircuitBreaker à utiliser
        fallback: Fonction de fallback en cas de circuit ouvert (optionnel)
    
    Usage:
        @with_circuit_breaker(sparkseer_breaker, fallback=get_cached_data)
        async def get_node_info(pubkey: str):
            return await api_call(pubkey)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.warning(f"Circuit breaker open for {func.__name__}: {str(e)}")
                
                if fallback:
                    logger.info(f"Using fallback for {func.__name__}")
                    try:
                        return await fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback failed for {func.__name__}: {str(fallback_error)}")
                        raise e
                else:
                    raise
        
        return wrapper
    return decorator


# ============================================================================
# CIRCUIT BREAKER MANAGER
# ============================================================================

class CircuitBreakerManager:
    """Gestionnaire centralisé de tous les circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        **kwargs
    ) -> CircuitBreaker:
        """Enregistre un nouveau circuit breaker"""
        if name in self.breakers:
            logger.warning(f"Circuit breaker '{name}' already exists, returning existing instance")
            return self.breakers[name]
        
        breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            **kwargs
        )
        
        self.breakers[name] = breaker
        logger.info(f"Circuit breaker '{name}' registered")
        return breaker
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Récupère un circuit breaker par nom"""
        return self.breakers.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Récupère les stats de tous les circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }
    
    def reset_all(self):
        """Réinitialise tous les circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")
    
    def health_check(self) -> Dict[str, Any]:
        """Retourne l'état de santé de tous les services"""
        health = {
            'healthy': [],
            'degraded': [],
            'unavailable': []
        }
        
        for name, breaker in self.breakers.items():
            state = breaker.get_state()
            stats = breaker.get_stats()
            
            if state == CircuitState.CLOSED and stats['success_rate'] > 0.9:
                health['healthy'].append(name)
            elif state == CircuitState.OPEN:
                health['unavailable'].append(name)
            else:
                health['degraded'].append(name)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_services': len(self.breakers),
            'healthy_count': len(health['healthy']),
            'degraded_count': len(health['degraded']),
            'unavailable_count': len(health['unavailable']),
            'services': health
        }


# Instance globale du manager
circuit_breaker_manager = CircuitBreakerManager()


# ============================================================================
# CIRCUIT BREAKERS PRÉDÉFINIS POUR MCP
# ============================================================================

# Sparkseer API
sparkseer_breaker = circuit_breaker_manager.register(
    name="sparkseer_api",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2
)

# Anthropic API
anthropic_breaker = circuit_breaker_manager.register(
    name="anthropic_api",
    failure_threshold=3,
    recovery_timeout=120,
    success_threshold=2
)

# Ollama Local (plus tolérant car local)
ollama_breaker = circuit_breaker_manager.register(
    name="ollama_local",
    failure_threshold=10,
    recovery_timeout=30,
    success_threshold=3
)

# LNBits
lnbits_breaker = circuit_breaker_manager.register(
    name="lnbits_api",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2
)

# MongoDB
mongodb_breaker = circuit_breaker_manager.register(
    name="mongodb",
    failure_threshold=10,
    recovery_timeout=30,
    success_threshold=3
)

# Redis
redis_breaker = circuit_breaker_manager.register(
    name="redis_cache",
    failure_threshold=10,
    recovery_timeout=30,
    success_threshold=3
)


logger.info("Circuit breakers initialized for all MCP services")

