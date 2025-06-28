"""
Circuit Breaker optimisé pour MCP avec async/await et métriques avancées
Inclut fenêtre glissante, monitoring et gestion d'erreurs robuste

Dernière mise à jour: 9 janvier 2025
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict, List, Union
from enum import Enum
from dataclasses import dataclass, field
import threading
from collections import deque

from config import settings
from src.logging_config import get_logger, log_performance

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """États du circuit breaker"""
    CLOSED = "closed"        # Normal, requêtes passent
    OPEN = "open"           # Erreurs détectées, requêtes bloquées
    HALF_OPEN = "half_open" # Test de récupération


@dataclass
class CircuitBreakerConfig:
    """Configuration d'un circuit breaker"""
    failure_threshold: int = 5                    # Seuil d'échecs pour ouvrir
    recovery_timeout: float = 60.0              # Timeout avant test de récupération
    execution_timeout: float = 10.0             # Timeout d'exécution
    success_threshold: int = 3                   # Succès requis en half-open pour fermer
    failure_rate_threshold: float = 0.5         # Taux d'échec pour ouvrir (50%)
    minimum_requests: int = 10                   # Minimum de requêtes avant calcul du taux
    sliding_window_size: int = 100              # Taille de la fenêtre glissante
    
    def __post_init__(self):
        if not 0 <= self.failure_rate_threshold <= 1:
            raise ValueError("failure_rate_threshold doit être entre 0 et 1")


@dataclass
class ExecutionResult:
    """Résultat d'une exécution via circuit breaker"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CircuitBreakerStats:
    """Statistiques du circuit breaker"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.executions: deque = deque(maxlen=window_size)
        self.state_changes: List[Dict] = []
        self._lock = threading.Lock()
    
    def record_execution(self, result: ExecutionResult):
        """Enregistre une exécution"""
        with self._lock:
            self.executions.append(result)
    
    def record_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState):
        """Enregistre un changement d'état"""
        with self._lock:
            self.state_changes.append({
                "from": old_state.value,
                "to": new_state.value,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Garde seulement les 50 derniers changements
            if len(self.state_changes) > 50:
                self.state_changes = self.state_changes[-50:]
    
    @property
    def total_requests(self) -> int:
        """Nombre total de requêtes"""
        return len(self.executions)
    
    @property
    def success_count(self) -> int:
        """Nombre de succès"""
        return sum(1 for exec in self.executions if exec.success)
    
    @property
    def failure_count(self) -> int:
        """Nombre d'échecs"""
        return sum(1 for exec in self.executions if not exec.success)
    
    @property
    def failure_rate(self) -> float:
        """Taux d'échec"""
        if not self.executions:
            return 0.0
        return self.failure_count / len(self.executions)
    
    @property
    def average_duration_ms(self) -> float:
        """Durée moyenne d'exécution"""
        if not self.executions:
            return 0.0
        return sum(exec.duration_ms for exec in self.executions) / len(self.executions)
    
    def get_recent_failures(self, minutes: int = 5) -> List[ExecutionResult]:
        """Retourne les échecs récents"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [
            exec for exec in self.executions 
            if not exec.success and exec.timestamp >= cutoff
        ]


class CircuitBreakerError(Exception):
    """Exception levée quand le circuit breaker est ouvert"""
    pass


class CircuitOpenError(CircuitBreakerError):
    """Exception pour compatibilité avec l'ancien code"""
    pass


class CircuitBreaker:
    """Circuit breaker optimisé avec fenêtre glissante et métriques"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats(self.config.sliding_window_size)
        
        # État interne
        self.last_failure_time: Optional[datetime] = None
        self.half_open_success_count = 0
        self._state_lock = threading.Lock()
        
        logger.info("Circuit breaker créé",
                   name=name,
                   config=self.config.__dict__)
    
    def _change_state(self, new_state: CircuitBreakerState, reason: str = ""):
        """Change l'état du circuit breaker"""
        if new_state == self.state:
            return
        
        old_state = self.state
        self.state = new_state
        
        # Réinitialise les compteurs selon l'état
        if new_state == CircuitBreakerState.HALF_OPEN:
            self.half_open_success_count = 0
        
        # Enregistre le changement
        self.stats.record_state_change(old_state, new_state)
        
        logger.warning("Circuit breaker changement d'état",
                      name=self.name,
                      from_state=old_state.value,
                      to_state=new_state.value,
                      reason=reason)
    
    def _should_open(self) -> bool:
        """Détermine si le circuit breaker doit s'ouvrir"""
        # Vérifie le seuil minimum de requêtes
        if self.stats.total_requests < self.config.minimum_requests:
            return False
        
        # Vérifie le taux d'échec
        failure_rate = self.stats.failure_rate
        return failure_rate >= self.config.failure_rate_threshold
    
    def _can_attempt_reset(self) -> bool:
        """Vérifie si on peut tenter une réinitialisation"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction via le circuit breaker"""
        with self._state_lock:
            current_state = self.state
        
        # Vérifie l'état du circuit breaker
        if current_state == CircuitBreakerState.OPEN:
            if self._can_attempt_reset():
                with self._state_lock:
                    self._change_state(CircuitBreakerState.HALF_OPEN, "timeout récupération")
                current_state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerError(f"Circuit breaker ouvert pour {self.name}")
        
        elif current_state == CircuitBreakerState.HALF_OPEN:
            # En half-open, on limite les tentatives
            if self.half_open_success_count >= self.config.success_threshold:
                with self._state_lock:
                    self._change_state(CircuitBreakerState.CLOSED, "récupération réussie")
        
        # Exécute la fonction avec timeout
        start_time = time.time()
        result = None
        error = None
        success = False
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.execution_timeout
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                )
            success = True
            
        except asyncio.TimeoutError as e:
            error = CircuitBreakerError(f"Timeout exécution {self.name}: {self.config.execution_timeout}s")
            logger.error("Timeout circuit breaker", name=self.name, timeout=self.config.execution_timeout)
            
        except Exception as e:
            error = e
            logger.error("Erreur via circuit breaker", name=self.name, error=str(e))
        
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Enregistre le résultat
            execution_result = ExecutionResult(
                success=success,
                result=result,
                error=error,
                duration_ms=duration_ms
            )
            self.stats.record_execution(execution_result)
            
            # Log de performance
            log_performance(f"circuit_breaker_{self.name}", duration_ms, success=success)
        
        # Gère les changements d'état selon le résultat
        with self._state_lock:
            self._handle_execution_result(success, error)
        
        if not success:
            raise error
        
        return result
    
    def _handle_execution_result(self, success: bool, error: Optional[Exception]):
        """Gère les changements d'état selon le résultat d'exécution"""
        if success:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_success_count += 1
                if self.half_open_success_count >= self.config.success_threshold:
                    self._change_state(CircuitBreakerState.CLOSED, "récupération complète")
        else:
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Échec en half-open -> retour à open
                self._change_state(CircuitBreakerState.OPEN, "échec en récupération")
            elif self.state == CircuitBreakerState.CLOSED:
                # Vérifie si on doit ouvrir
                if self._should_open():
                    self._change_state(CircuitBreakerState.OPEN, "seuil d'échec atteint")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du circuit breaker"""
        return {
            "name": self.name,
            "state": self.state.value,
            "config": self.config.__dict__,
            "stats": {
                "total_requests": self.stats.total_requests,
                "success_count": self.stats.success_count,
                "failure_count": self.stats.failure_count,
                "failure_rate": self.stats.failure_rate,
                "average_duration_ms": self.stats.average_duration_ms
            },
            "recent_failures": len(self.stats.get_recent_failures()),
            "state_changes": self.stats.state_changes[-5:],  # 5 derniers changements
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Méthode de compatibilité avec l'ancien code"""
        return self.get_stats()
    
    def reset(self):
        """Remet à zéro le circuit breaker"""
        with self._state_lock:
            self._change_state(CircuitBreakerState.CLOSED, "reset manuel")
            self.last_failure_time = None
            self.half_open_success_count = 0
            self.stats = CircuitBreakerStats(self.config.sliding_window_size)
        
        logger.info("Circuit breaker réinitialisé", name=self.name)


class CircuitBreakerRegistry:
    """Registre global des circuit breakers"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers = {}
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_breakers'):
            self._breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get(cls, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Récupère ou crée un circuit breaker"""
        instance = cls()
        
        if name not in instance._breakers:
            instance._breakers[name] = CircuitBreaker(name, config)
            logger.info("Nouveau circuit breaker enregistré", name=name)
        
        return instance._breakers[name]
    
    @classmethod
    def get_all(cls) -> Dict[str, CircuitBreaker]:
        """Retourne tous les circuit breakers"""
        instance = cls()
        return instance._breakers.copy()
    
    @classmethod
    def get_all_metrics(cls) -> Dict[str, Dict[str, Any]]:
        """Récupère les métriques de tous les circuit breakers"""
        instance = cls()
        return {name: cb.get_stats() for name, cb in instance._breakers.items()}
    
    @classmethod
    def get_stats_summary(cls) -> Dict[str, Any]:
        """Retourne un résumé des statistiques de tous les circuit breakers"""
        instance = cls()
        summary = {
            "total_breakers": len(instance._breakers),
            "states": {"closed": 0, "open": 0, "half_open": 0},
            "breakers": {}
        }
        
        for name, breaker in instance._breakers.items():
            stats = breaker.get_stats()
            summary["breakers"][name] = stats
            summary["states"][stats["state"]] += 1
        
        return summary
    
    @classmethod
    def reset_all(cls):
        """Réinitialise tous les circuit breakers"""
        instance = cls()
        for cb in instance._breakers.values():
            cb.reset()
        logger.info("Tous les circuit breakers réinitialisés")


# Décorateur pour faciliter l'utilisation (compatible avec l'ancien code)
def circuit_protected(circuit_name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Décorateur pour protéger une fonction avec un circuit breaker.
    
    Usage:
        @circuit_protected("external_api")
        async def call_external_api():
            ...
    """
    circuit = CircuitBreakerRegistry.get(circuit_name, config)
    
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit.execute(func, *args, **kwargs)
        return wrapper
    return decorator 