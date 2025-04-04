import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from src.network_analyzer import NetworkAnalyzer
from src.redis_operations import RedisOperations
from src.models import NodeData, ChannelData, ChannelRecommendation, NetworkMetrics

@pytest.fixture
def mock_redis_ops():
    """Fixture pour simuler les opérations Redis"""
    redis_ops = Mock(spec=RedisOperations)
    redis_ops.get_node_data = AsyncMock()
    redis_ops.get_all_nodes = AsyncMock()
    redis_ops.get_node_channels = AsyncMock()
    redis_ops.get_network_metrics = AsyncMock()
    return redis_ops

@pytest.fixture
def analyzer(mock_redis_ops):
    """Fixture pour l'analyseur de réseau"""
    return NetworkAnalyzer(mock_redis_ops)

@pytest.fixture
def sample_node():
    """Fixture pour un nœud de test"""
    return NodeData(
        node_id="test_node_id",
        alias="Test Node",
        capacity=1_000_000_000,  # 10 BTC
        channel_count=50,
        last_update=datetime.now(),
        reputation_score=95.0
    )

@pytest.fixture
def sample_channel():
    """Fixture pour un canal de test"""
    return ChannelData(
        channel_id="test_channel_id",
        capacity=100_000_000,  # 1 BTC
        fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
        balance={"local": 0.5, "remote": 0.5},
        age=30,
        last_update=datetime.now()
    )

@pytest.fixture
def sample_network_metrics():
    """Fixture pour les métriques réseau"""
    return NetworkMetrics(
        total_capacity=100_000_000_000,  # 1000 BTC
        total_channels=50000,
        total_nodes=10000,
        average_fee_rate=0.0001,
        last_update=datetime.now()
    )

@pytest.mark.asyncio
async def test_analyze_node_connections(analyzer, mock_redis_ops, sample_node):
    """Test de l'analyse des connexions d'un nœud"""
    # Configuration des mocks
    mock_redis_ops.get_node_data.return_value = sample_node
    mock_redis_ops.get_all_nodes.return_value = [
        NodeData(
            node_id="target1",
            alias="Target 1",
            capacity=2_000_000_000,
            channel_count=100,
            last_update=datetime.now(),
            reputation_score=98.0
        ),
        NodeData(
            node_id="target2",
            alias="Target 2",
            capacity=500_000_000,
            channel_count=20,
            last_update=datetime.now(),
            reputation_score=85.0
        )
    ]
    
    # Exécution du test
    recommendations = await analyzer.analyze_node_connections("test_node_id")
    
    # Vérifications
    assert len(recommendations) > 0
    assert all(isinstance(r, ChannelRecommendation) for r in recommendations)
    assert all(r.source_node_id == "test_node_id" for r in recommendations)
    assert recommendations[0].score > recommendations[-1].score  # Vérifie le tri par score

@pytest.mark.asyncio
async def test_calculate_balance_score(analyzer, mock_redis_ops, sample_node):
    """Test du calcul du score d'équilibre"""
    # Configuration des mocks
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
        )
    ]
    
    # Exécution du test
    score = await analyzer._calculate_balance_score(sample_node)
    
    # Vérifications
    assert 0 <= score <= 1
    assert score == 0.5  # Un canal équilibré sur deux

@pytest.mark.asyncio
async def test_calculate_recommended_capacity(analyzer, mock_redis_ops, sample_node):
    """Test du calcul de la capacité recommandée"""
    # Configuration des mocks
    mock_redis_ops.get_node_channels.return_value = [
        ChannelData(
            channel_id="ch1",
            capacity=100_000_000,  # 1 BTC
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now()
        ),
        ChannelData(
            channel_id="ch2",
            capacity=200_000_000,  # 2 BTC
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now()
        )
    ]
    
    # Exécution du test
    capacity = await analyzer._calculate_recommended_capacity(
        sample_node,
        NodeData(
            node_id="target",
            alias="Target",
            capacity=2_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        )
    )
    
    # Vérifications
    assert "min" in capacity
    assert "max" in capacity
    assert capacity["min"] <= capacity["max"]
    assert capacity["min"] >= 0.01
    assert capacity["max"] <= 0.1

@pytest.mark.asyncio
async def test_calculate_recommended_fees(analyzer, mock_redis_ops, sample_network_metrics):
    """Test du calcul des frais recommandés"""
    # Configuration des mocks
    mock_redis_ops.get_network_metrics.return_value = sample_network_metrics
    
    # Exécution du test
    fees = await analyzer._calculate_recommended_fees(
        NodeData(
            node_id="source",
            alias="Source",
            capacity=1_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        ),
        NodeData(
            node_id="target",
            alias="Target",
            capacity=2_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        )
    )
    
    # Vérifications
    assert "base_fee" in fees
    assert "fee_rate" in fees
    assert fees["base_fee"] == 1000
    assert fees["fee_rate"] == 0.00008  # 80% du taux moyen

@pytest.mark.asyncio
async def test_get_network_insights(analyzer, mock_redis_ops, sample_network_metrics):
    """Test de la génération des insights réseau"""
    # Configuration des mocks
    mock_redis_ops.get_network_metrics.return_value = sample_network_metrics
    mock_redis_ops.get_all_nodes.return_value = [
        NodeData(
            node_id="node1",
            alias="Node 1",
            capacity=1_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        ),
        NodeData(
            node_id="node2",
            alias="Node 2",
            capacity=2_000_000_000,
            channel_count=100,
            last_update=datetime.now(),
            reputation_score=98.0
        )
    ]
    
    # Exécution du test
    insights = await analyzer.get_network_insights()
    
    # Vérifications
    assert "total_nodes" in insights
    assert "total_channels" in insights
    assert "total_capacity" in insights
    assert "average_capacity" in insights
    assert "average_channels" in insights
    assert "average_reputation" in insights
    assert "network_fee_rate" in insights
    assert "last_update" in insights
    
    assert insights["total_nodes"] == 2
    assert insights["total_channels"] == 150
    assert insights["total_capacity"] == 3_000_000_000
    assert insights["average_capacity"] == 1_500_000_000
    assert insights["average_channels"] == 75
    assert insights["average_reputation"] == 96.5
    assert insights["network_fee_rate"] == 0.0001 