import pytest
from unittest.mock import Mock, AsyncMock, patch
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
        reputation_score=95.0,
        location={"country": "France", "region": "Île-de-France", "city": "Paris"},
        uptime=0.98
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
        last_update=datetime.now(),
        status="active",
        policies={
            "node1": {"min_htlc": 1000, "max_htlc": 100_000_000},
            "node2": {"min_htlc": 1000, "max_htlc": 100_000_000}
        }
    )

@pytest.fixture
def sample_network_metrics():
    """Fixture pour les métriques réseau"""
    return NetworkMetrics(
        total_capacity=100_000_000_000,  # 1000 BTC
        total_channels=50000,
        total_nodes=10000,
        average_fee_rate=0.0001,
        last_update=datetime.now(),
        active_nodes_percentage=0.85,
        average_channel_age=180
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
            reputation_score=98.0,
            location={"country": "Germany", "region": "Berlin", "city": "Berlin"},
            uptime=0.99
        ),
        NodeData(
            node_id="target2",
            alias="Target 2",
            capacity=500_000_000,
            channel_count=20,
            last_update=datetime.now(),
            reputation_score=85.0,
            location={"country": "Spain", "region": "Catalonia", "city": "Barcelona"},
            uptime=0.95
        )
    ]
    
    # Mock pour _analyze_potential_connection pour tester directement analyze_node_connections
    analyzer._analyze_potential_connection = AsyncMock(side_effect=[
        ChannelRecommendation(
            source_node_id="test_node_id",
            target_node_id="target1",
            score=0.9,
            capacity_recommendation={"min": 0.01, "max": 0.05},
            fee_recommendation={"base_fee": 1000, "fee_rate": 0.0001},
            created_at=datetime.now()
        ),
        ChannelRecommendation(
            source_node_id="test_node_id",
            target_node_id="target2",
            score=0.7,
            capacity_recommendation={"min": 0.01, "max": 0.03},
            fee_recommendation={"base_fee": 800, "fee_rate": 0.00008},
            created_at=datetime.now()
        )
    ])
    
    # Exécution du test
    recommendations = await analyzer.analyze_node_connections("test_node_id")
    
    # Vérifications
    assert len(recommendations) == 2
    assert all(isinstance(r, ChannelRecommendation) for r in recommendations)
    assert all(r.source_node_id == "test_node_id" for r in recommendations)
    assert recommendations[0].score > recommendations[-1].score  # Vérifie le tri par score
    assert mock_redis_ops.get_node_data.call_count == 1
    assert mock_redis_ops.get_all_nodes.call_count == 1
    assert analyzer._analyze_potential_connection.call_count == 2

@pytest.mark.asyncio
async def test_analyze_potential_connection(analyzer, mock_redis_ops, sample_node):
    """Test de l'analyse d'une connexion potentielle entre deux nœuds"""
    # Configuration du test
    source_node = sample_node
    target_node = NodeData(
        node_id="target_node_id",
        alias="Target Node",
        capacity=2_000_000_000,
        channel_count=100,
        last_update=datetime.now(),
        reputation_score=98.0,
        location={"country": "Germany", "region": "Berlin", "city": "Berlin"},
        uptime=0.99
    )
    
    # Mock des méthodes auxiliaires
    analyzer._calculate_balance_score = AsyncMock(return_value=0.8)
    analyzer._calculate_recommended_capacity = AsyncMock(return_value={"min": 0.01, "max": 0.05})
    analyzer._calculate_recommended_fees = AsyncMock(return_value={"base_fee": 1000, "fee_rate": 0.0001})
    
    # Exécution du test
    recommendation = await analyzer._analyze_potential_connection(source_node, target_node)
    
    # Vérifications
    assert recommendation is not None
    assert recommendation.source_node_id == source_node.node_id
    assert recommendation.target_node_id == target_node.node_id
    assert recommendation.score > 0
    assert "min" in recommendation.capacity_recommendation
    assert "max" in recommendation.capacity_recommendation
    assert "base_fee" in recommendation.fee_recommendation
    assert "fee_rate" in recommendation.fee_recommendation

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
            last_update=datetime.now(),
            status="active"
        ),
        ChannelData(
            channel_id="ch2",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.8, "remote": 0.2},
            age=30,
            last_update=datetime.now(),
            status="active"
        ),
        ChannelData(
            channel_id="ch3",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.6, "remote": 0.4},
            age=30,
            last_update=datetime.now(),
            status="active"
        )
    ]
    
    # Exécution du test
    score = await analyzer._calculate_balance_score(sample_node)
    
    # Vérifications
    assert 0 <= score <= 1
    assert score == 2/3  # Deux canaux sur trois sont équilibrés (<20% de différence)

@pytest.mark.asyncio
async def test_calculate_balance_score_no_channels(analyzer, mock_redis_ops, sample_node):
    """Test du calcul du score d'équilibre sans canaux"""
    # Configuration des mocks
    mock_redis_ops.get_node_channels.return_value = []
    
    # Exécution du test
    score = await analyzer._calculate_balance_score(sample_node)
    
    # Vérifications
    assert score == 0.0

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
            last_update=datetime.now(),
            status="active"
        ),
        ChannelData(
            channel_id="ch2",
            capacity=200_000_000,  # 2 BTC
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now(),
            status="active"
        )
    ]
    
    # Exécution du test
    target_node = NodeData(
            node_id="target",
            alias="Target",
            capacity=2_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        )
    
    capacity = await analyzer._calculate_recommended_capacity(sample_node, target_node)
    
    # Vérifications
    assert "min" in capacity
    assert "max" in capacity
    assert capacity["min"] <= capacity["max"]
    assert capacity["min"] >= 0.01
    assert capacity["max"] <= 0.1
    # On peut être plus précis sur les valeurs attendues basées sur la logique de calcul
    expected_avg = 1.5  # (1 + 2) / 2 BTC
    expected_min = max(0.01, min(0.05, expected_avg * 0.5 * 0.8))
    expected_max = min(0.1, expected_avg * 1.5 * 0.8)
    assert abs(capacity["min"] - expected_min) < 0.001
    assert abs(capacity["max"] - expected_max) < 0.001

@pytest.mark.asyncio
async def test_calculate_recommended_capacity_no_channels(analyzer, mock_redis_ops, sample_node):
    """Test du calcul de la capacité recommandée sans canaux existants"""
    # Configuration des mocks
    mock_redis_ops.get_node_channels.return_value = []
    
    # Exécution du test
    target_node = NodeData(
        node_id="target",
        alias="Target",
        capacity=2_000_000_000,
        channel_count=0,
        last_update=datetime.now(),
        reputation_score=95.0
    )
    
    capacity = await analyzer._calculate_recommended_capacity(sample_node, target_node)
    
    # Vérifications
    assert capacity == {"min": 0.01, "max": 0.1}  # Valeurs par défaut

@pytest.mark.asyncio
async def test_calculate_recommended_fees(analyzer, mock_redis_ops, sample_network_metrics):
    """Test du calcul des frais recommandés"""
    # Configuration des mocks
    mock_redis_ops.get_network_metrics.return_value = sample_network_metrics
    mock_redis_ops.get_node_channels.return_value = [
        ChannelData(
            channel_id="ch1",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now(),
            status="active"
        ),
        ChannelData(
            channel_id="ch2",
            capacity=200_000_000,
            fee_rate={"base_fee": 1500, "fee_rate": 0.00015},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now(),
            status="active"
        )
    ]
    
    # Exécution du test
    source_node = NodeData(
            node_id="source",
            alias="Source",
            capacity=1_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
    )
    
    target_node = NodeData(
            node_id="target",
            alias="Target",
            capacity=2_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0
        )
    
    fees = await analyzer._calculate_recommended_fees(source_node, target_node)
    
    # Vérifications
    assert "base_fee" in fees
    assert "fee_rate" in fees
    # Calcul des valeurs attendues
    expected_base_fee = int((1000 + 1500) / 2 * 0.8)  # Moyenne * facteur de liquidité
    expected_fee_rate = (0.0001 + 0.00015) / 2 * 0.8
    assert fees["base_fee"] == expected_base_fee
    assert abs(fees["fee_rate"] - expected_fee_rate) < 0.000001

@pytest.mark.asyncio
async def test_calculate_recommended_fees_no_channels(analyzer, mock_redis_ops):
    """Test du calcul des frais recommandés sans canaux existants"""
    # Configuration des mocks
    mock_redis_ops.get_node_channels.return_value = []
    
    # Exécution du test
    source_node = NodeData(
        node_id="source",
        alias="Source",
        capacity=1_000_000_000,
        channel_count=50,
        last_update=datetime.now(),
        reputation_score=95.0
    )
    
    target_node = NodeData(
        node_id="target",
        alias="Target",
        capacity=2_000_000_000,
        channel_count=0,
        last_update=datetime.now(),
        reputation_score=95.0
    )
    
    fees = await analyzer._calculate_recommended_fees(source_node, target_node)
    
    # Vérifications
    assert fees == {"base_fee": 1000, "fee_rate": 0.00008}  # Valeurs par défaut

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
            reputation_score=95.0,
            uptime=0.98
        ),
        NodeData(
            node_id="node2",
            alias="Node 2",
            capacity=2_000_000_000,
            channel_count=100,
            last_update=datetime.now(),
            reputation_score=98.0,
            uptime=0.99
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

@pytest.mark.asyncio
async def test_get_network_insights_no_data(analyzer, mock_redis_ops):
    """Test de la génération des insights réseau sans données"""
    # Configuration des mocks
    mock_redis_ops.get_network_metrics.return_value = None
    mock_redis_ops.get_all_nodes.return_value = []
    
    # Exécution du test
    insights = await analyzer.get_network_insights()
    
    # Vérifications
    assert insights == {} 