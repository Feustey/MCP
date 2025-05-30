import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from src.network_optimizer import NetworkOptimizer
from src.redis_operations import RedisOperations
from src.models import NodeData, ChannelData, ChannelRecommendation, NetworkMetrics

@pytest.fixture
def mock_redis_ops():
    """Fixture pour simuler les opérations Redis"""
    redis_ops = Mock(spec=RedisOperations)
    redis_ops.update_channel_stats = AsyncMock()
    redis_ops.get_channel_data = AsyncMock()
    redis_ops.update_channel_fees = AsyncMock()
    redis_ops.save_rebalance_suggestion = AsyncMock()
    redis_ops.save_channel_closure_suggestion = AsyncMock()
    redis_ops.get_node_data = AsyncMock()
    redis_ops.get_node_channels = AsyncMock()
    return redis_ops

@pytest.fixture
def optimizer(mock_redis_ops):
    """Fixture pour l'optimiseur de réseau"""
    return NetworkOptimizer(mock_redis_ops)

@pytest.fixture
def sample_channel():
    """Fixture pour un canal de test"""
    return ChannelData(
        channel_id="test_channel_id",
        capacity=100_000_000,
        fee_rate={"base_fee": 1000.0, "fee_rate": 0.0001},
        balance={"local": 0.5, "remote": 0.5},
        age=30,
        last_update=datetime.now(),
        metadata={}
    )

@pytest.mark.asyncio
async def test_monitor_routing_performance(optimizer):
    """Test du monitoring des performances de routage"""
    # Test d'une route réussie
    await optimizer.monitor_routing_performance("test_channel_id", 1000000, True, 200.0)
    
    # Vérification des statistiques
    stats = optimizer.routing_stats.get("test_channel_id")
    assert stats is not None
    assert stats["total_attempts"] == 1
    assert stats["successful_routes"] == 1
    assert stats["total_latency"] == 200.0
    
    # Test d'une route échouée
    await optimizer.monitor_routing_performance("test_channel_id", 1000000, False, 0.0)
    
    # Vérification des statistiques mises à jour
    stats = optimizer.routing_stats.get("test_channel_id")
    assert stats["total_attempts"] == 2
    assert stats["successful_routes"] == 1  # Inchangé
    assert stats["total_latency"] == 200.0  # Inchangé
    
    # Vérification des appels à Redis
    assert optimizer.redis_ops.update_channel_stats.call_count == 2

@pytest.mark.asyncio
async def test_check_channel_performance(optimizer, sample_channel):
    """Test de la vérification des performances d'un canal"""
    # Configuration du mock
    optimizer.redis_ops.get_channel_data.return_value = sample_channel
    
    # Configuration des statistiques
    optimizer.routing_stats["test_channel_id"] = {
        "total_attempts": 10,
        "successful_routes": 7,
        "total_latency": 1500.0,
        "last_update": datetime.now()
    }
    
    # Test de la vérification
    await optimizer._check_channel_performance("test_channel_id")
    
    # Vérification des appels
    assert optimizer.redis_ops.get_channel_data.called
    assert optimizer.redis_ops.update_channel_fees.called

@pytest.mark.asyncio
async def test_adjust_channel_fees(optimizer, sample_channel):
    """Test de l'ajustement des frais d'un canal"""
    # Test avec un faible taux de succès
    await optimizer._adjust_channel_fees(sample_channel, 0.7, 600.0)
    
    # Vérification de l'appel à Redis
    assert optimizer.redis_ops.update_channel_fees.called
    call_args = optimizer.redis_ops.update_channel_fees.call_args[0]
    assert call_args[0] == sample_channel.channel_id
    assert call_args[1]["base_fee"] == sample_channel.fee_rate["base_fee"]
    assert call_args[1]["fee_rate"] > sample_channel.fee_rate["fee_rate"]

@pytest.mark.asyncio
async def test_handle_bottleneck(optimizer, sample_channel):
    """Test de la gestion des goulets d'étranglement"""
    # Test avec un canal déséquilibré
    unbalanced_channel = ChannelData(
        channel_id="unbalanced_channel",
        capacity=100_000_000,
        fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
        balance={"local": 0.9, "remote": 0.1},
        age=30,
        last_update=datetime.now()
    )
    
    await optimizer._handle_bottleneck(unbalanced_channel)
    
    # Vérification qu'une suggestion de rebalance a été créée
    assert optimizer.redis_ops.save_rebalance_suggestion.called

@pytest.mark.asyncio
async def test_suggest_rebalance(optimizer):
    """Test de la suggestion de rebalance"""
    # Test avec un canal déséquilibré (trop de liquidité locale)
    channel = ChannelData(
        channel_id="test_channel",
        capacity=100_000_000,
        fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
        balance={"local": 0.9, "remote": 0.1},
        age=30,
        last_update=datetime.now()
    )
    
    await optimizer._suggest_rebalance(channel)
    
    # Vérification de la suggestion
    assert optimizer.redis_ops.save_rebalance_suggestion.called
    suggestion = optimizer.redis_ops.save_rebalance_suggestion.call_args[0][0]
    assert suggestion["channel_id"] == "test_channel"
    assert suggestion["action"] == "rebalance"
    assert suggestion["direction"] == "outgoing"

@pytest.mark.asyncio
async def test_suggest_channel_closure(optimizer):
    """Test de la suggestion de fermeture de canal"""
    # Configuration des statistiques de routage
    optimizer.routing_stats["test_channel"] = {
        "total_attempts": 10,
        "successful_routes": 3,
        "total_latency": 3000.0,
        "last_update": datetime.now()
    }
    
    # Test avec un canal sous-performant
    channel = ChannelData(
        channel_id="test_channel",
        capacity=100_000_000,
        fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
        balance={"local": 0.5, "remote": 0.5},
        age=30,
        last_update=datetime.now()
    )
    
    await optimizer._suggest_channel_closure(channel)
    
    # Vérification de la suggestion
    assert optimizer.redis_ops.save_channel_closure_suggestion.called
    suggestion = optimizer.redis_ops.save_channel_closure_suggestion.call_args[0][0]
    assert suggestion["channel_id"] == "test_channel"
    assert suggestion["action"] == "close"
    assert suggestion["reason"] == "low_success_rate"

@pytest.mark.asyncio
async def test_analyze_node_health(optimizer, mock_redis_ops):
    """Test de l'analyse de la santé d'un nœud"""
    # Configuration des mocks
    mock_redis_ops.get_node_data.return_value = NodeData(
        node_id="test_node",
        alias="Test Node",
        capacity=1_000_000_000,
        channel_count=5,
        last_update=datetime.now(),
        reputation_score=95.0
    )
    
    mock_redis_ops.get_node_channels.return_value = [
        ChannelData(
            channel_id="ch1",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now()
        ),
        ChannelData(
            channel_id="ch2",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.8, "remote": 0.2},
            age=30,
            last_update=datetime.now()
        ),
        ChannelData(
            channel_id="ch3",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.2, "remote": 0.8},
            age=30,
            last_update=datetime.now()
        )
    ]
    
    # Configuration des statistiques de routage
    optimizer.routing_stats["ch1"] = {
        "total_attempts": 10,
        "successful_routes": 9,
        "total_latency": 2000.0,
        "last_update": datetime.now()
    }
    
    optimizer.routing_stats["ch2"] = {
        "total_attempts": 10,
        "successful_routes": 5,
        "total_latency": 5000.0,
        "last_update": datetime.now()
    }
    
    optimizer.routing_stats["ch3"] = {
        "total_attempts": 10,
        "successful_routes": 8,
        "total_latency": 3000.0,
        "last_update": datetime.now()
    }
    
    # Test de l'analyse
    health = await optimizer.analyze_node_health("test_node")
    
    # Vérifications
    assert health["node_id"] == "test_node"
    assert "total_capacity" in health
    assert "total_channels" in health
    assert "average_channel_size" in health
    assert "balance_ratio" in health
    assert "bottleneck_channels" in health
    assert "underperforming_channels" in health
    assert "last_update" in health

@pytest.mark.asyncio
async def test_get_optimization_suggestions(optimizer, mock_redis_ops):
    """Test de la génération des suggestions d'optimisation"""
    # Configuration des mocks
    mock_redis_ops.get_node_data.return_value = NodeData(
        node_id="test_node",
        alias="Test Node",
        capacity=1_000_000_000,
        channel_count=5,
        last_update=datetime.now(),
        reputation_score=95.0
    )
    
    mock_redis_ops.get_node_channels.return_value = [
        ChannelData(
            channel_id="ch1",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now()
        ),
        ChannelData(
            channel_id="ch2",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.8, "remote": 0.2},
            age=30,
            last_update=datetime.now()
        ),
        ChannelData(
            channel_id="ch3",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.2, "remote": 0.8},
            age=30,
            last_update=datetime.now()
        )
    ]
    
    # Configuration des statistiques de routage
    optimizer.routing_stats["ch1"] = {
        "total_attempts": 10,
        "successful_routes": 5,
        "total_latency": 5000.0,
        "last_update": datetime.now()
    }
    
    optimizer.routing_stats["ch2"] = {
        "total_attempts": 10,
        "successful_routes": 5,
        "total_latency": 5000.0,
        "last_update": datetime.now()
    }
    
    optimizer.routing_stats["ch3"] = {
        "total_attempts": 10,
        "successful_routes": 5,
        "total_latency": 5000.0,
        "last_update": datetime.now()
    }
    
    # Ajout d'un canal comme goulet d'étranglement
    optimizer.bottleneck_channels.add("ch2")
    
    # Test de la génération des suggestions
    suggestions = await optimizer.get_optimization_suggestions("test_node")
    
    # Vérifications
    assert len(suggestions) > 0
    assert any(s["type"] == "performance" and s["action"] == "monitor" for s in suggestions)
    assert any(s["type"] == "balance" and s["action"] == "rebalance" for s in suggestions) 