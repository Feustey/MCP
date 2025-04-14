import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from src.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
    circuit_protected,
    CircuitBreakerRegistry
)

@pytest.fixture
def circuit_breaker():
    """Fixture pour un circuit breaker avec une configuration de test"""
    config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=1.0,
        reset_timeout=1.0,
        execution_timeout=1.0
    )
    return CircuitBreaker("test_circuit", config)

class TestException(Exception):
    """Exception pour les tests"""
    pass

class TestExcludedException(Exception):
    """Exception exclue pour les tests"""
    pass

@pytest.mark.asyncio
async def test_circuit_breaker_initial_state(circuit_breaker):
    """Test de l'état initial du circuit breaker"""
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    
    # Test d'une exécution réussie
    mock_func = AsyncMock(return_value="success")
    result = await circuit_breaker.execute(mock_func)
    
    assert result == "success"
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0
    assert circuit_breaker.metrics["success_count"] == 1

@pytest.mark.asyncio
async def test_circuit_breaker_failures(circuit_breaker):
    """Test du circuit breaker lors de plusieurs échecs consécutifs"""
    mock_func = AsyncMock(side_effect=TestException("Test error"))
    
    # Premier échec
    with pytest.raises(TestException):
        await circuit_breaker.execute(mock_func)
    
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 1
    
    # Deuxième échec, devrait ouvrir le circuit
    with pytest.raises(TestException):
        await circuit_breaker.execute(mock_func)
    
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.failure_count == 2
    
    # Tentative en circuit ouvert, devrait lever CircuitOpenError
    with pytest.raises(CircuitOpenError):
        await circuit_breaker.execute(mock_func)
    
    assert circuit_breaker.metrics["rejected_count"] == 1

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    """Test de la récupération du circuit breaker après le délai de recovery"""
    mock_func = AsyncMock(side_effect=[TestException("Test error"), TestException("Test error"), "success"])
    
    # Ouvrir le circuit avec deux échecs
    with pytest.raises(TestException):
        await circuit_breaker.execute(mock_func)
    with pytest.raises(TestException):
        await circuit_breaker.execute(mock_func)
    
    assert circuit_breaker.state == CircuitState.OPEN
    
    # Attendre le délai de recovery
    await asyncio.sleep(1.1)
    
    # Prochain appel devrait être en half-open
    result = await circuit_breaker.execute(mock_func)
    assert result == "success"
    
    # Attendre le délai de reset
    await asyncio.sleep(1.1)
    
    # Vérifier la transition vers closed
    assert circuit_breaker.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_timeout(circuit_breaker):
    """Test du timeout d'exécution"""
    # Une fonction qui prend trop de temps
    async def slow_func():
        await asyncio.sleep(2.0)
        return "never reached"
    
    # Devrait lever un TimeoutError et incrémenter failure_count
    with pytest.raises(asyncio.TimeoutError):
        await circuit_breaker.execute(slow_func)
    
    assert circuit_breaker.failure_count == 1
    assert circuit_breaker.metrics["timeout_count"] == 1

@pytest.mark.asyncio
async def test_excluded_exceptions(circuit_breaker):
    """Test des exceptions exclues"""
    # Configurer le circuit breaker pour exclure certaines exceptions
    circuit_breaker.config.exclude_exceptions = [TestExcludedException]
    
    # Mock func qui lève des exceptions exclues
    mock_func = AsyncMock(side_effect=TestExcludedException("Excluded"))
    
    # Les exceptions exclues ne devraient pas incrémenter failure_count
    for _ in range(3):  # Plus que le seuil d'échec
        with pytest.raises(TestExcludedException):
            await circuit_breaker.execute(mock_func)
    
    # Le circuit devrait rester fermé malgré les erreurs
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.failure_count == 0

@pytest.mark.asyncio
async def test_circuit_breaker_decorator():
    """Test du décorateur circuit_protected"""
    test_calls = 0
    
    @circuit_protected("decorator_test", CircuitBreakerConfig(failure_threshold=2))
    async def test_func():
        nonlocal test_calls
        test_calls += 1
        if test_calls <= 2:
            raise TestException("Test error")
        return "success"
    
    # Premier appel - échec
    with pytest.raises(TestException):
        await test_func()
    
    # Deuxième appel - échec et ouverture du circuit
    with pytest.raises(TestException):
        await test_func()
    
    # Troisième appel - circuit ouvert
    with pytest.raises(CircuitOpenError):
        await test_func()

@pytest.mark.asyncio
async def test_circuit_breaker_registry():
    """Test du registre central de circuit breakers"""
    # Réinitialiser le registre
    CircuitBreakerRegistry._instances = {}
    
    # Obtenir deux instances
    cb1 = CircuitBreakerRegistry.get("service1")
    cb2 = CircuitBreakerRegistry.get("service2")
    
    assert len(CircuitBreakerRegistry._instances) == 2
    assert cb1.name == "service1"
    assert cb2.name == "service2"
    
    # Vérifier que la même instance est renvoyée
    cb1_again = CircuitBreakerRegistry.get("service1")
    assert cb1 is cb1_again
    
    # Test get_all_metrics
    metrics = CircuitBreakerRegistry.get_all_metrics()
    assert "service1" in metrics
    assert "service2" in metrics
    
    # Test reset_all
    CircuitBreakerRegistry.reset_all()
    for cb in CircuitBreakerRegistry._instances.values():
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0 