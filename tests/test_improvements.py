import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
from lnplus_integration.metrics import LNPlusMetrics
from lnplus_integration.circuit_breaker import LNPlusCircuitBreaker
from lnplus_integration.rate_limiter import AdaptiveRateLimiter
from lnplus_integration.exceptions import LNPlusNetworkError

@pytest.fixture
def metrics():
    return LNPlusMetrics()

@pytest.fixture
def circuit_breaker():
    return LNPlusCircuitBreaker()

@pytest.fixture
def rate_limiter():
    return AdaptiveRateLimiter()

@pytest.mark.asyncio
async def test_metrics_recording(metrics):
    """Test l'enregistrement des métriques"""
    metrics.record_request("GET", "/test", "200", 0.5)
    assert metrics.request_counter._value.get() == 1
    assert metrics.latency._sum.get() == 0.5

@pytest.mark.asyncio
async def test_circuit_breaker(circuit_breaker):
    """Test le circuit breaker"""
    # Test état fermé
    assert circuit_breaker.state == "closed"
    
    # Test échecs successifs
    for _ in range(4):
        with pytest.raises(LNPlusNetworkError):
            await circuit_breaker.execute(lambda: 1/0)
    
    assert circuit_breaker.state == "open"
    
    # Test réinitialisation
    circuit_breaker.reset()
    assert circuit_breaker.state == "closed"
    assert circuit_breaker.failure_count == 0

@pytest.mark.asyncio
async def test_rate_limiter(rate_limiter):
    """Test le rate limiter"""
    # Test limite par défaut
    for _ in range(60):
        assert not await rate_limiter.should_throttle()
    
    # La 61ème requête devrait être limitée
    assert await rate_limiter.should_throttle()
    
    # Test priorité haute
    for _ in range(120):
        assert not await rate_limiter.should_throttle("high_priority")
    
    # La 121ème requête devrait être limitée
    assert await rate_limiter.should_throttle("high_priority")

@pytest.mark.asyncio
async def test_rate_limit_adjustment(rate_limiter):
    """Test l'ajustement des limites de taux"""
    rate_limiter.adjust_rate_limit("default", 30)
    assert rate_limiter.rate_limits["default"] == 30
    
    for _ in range(30):
        assert not await rate_limiter.should_throttle()
    
    assert await rate_limiter.should_throttle()

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(circuit_breaker):
    """Test la récupération du circuit breaker"""
    # Mettre le circuit breaker en état ouvert
    circuit_breaker.state = "open"
    circuit_breaker.last_state_change = datetime.now() - timedelta(seconds=61)
    
    # Devrait passer en état semi-ouvert
    assert circuit_breaker._should_retry()
    assert circuit_breaker.state == "half-open"
    
    # Test réussite en état semi-ouvert
    result = await circuit_breaker.execute(lambda: "success")
    assert result == "success"
    assert circuit_breaker.state == "closed"

@pytest.mark.asyncio
async def test_metrics_updates(metrics):
    """Test les mises à jour des métriques"""
    metrics.update_balance(1000000)
    assert metrics.balance_gauge._value.get() == 1000000
    
    metrics.update_node_count(10)
    assert metrics.node_count._value.get() == 10
    
    metrics.update_swap_count(5)
    assert metrics.swap_count._value.get() == 5 