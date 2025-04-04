import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from bs4 import BeautifulSoup
from datetime import datetime
from src.amboss_scraper import AmbossScraper
from src.redis_operations import RedisOperations
from src.models import NodeData, ChannelData, NetworkMetrics

@pytest.fixture
def mock_redis_ops():
    """Fixture pour simuler les opérations Redis"""
    redis_ops = Mock(spec=RedisOperations)
    redis_ops.cache_node_data = AsyncMock(return_value=True)
    redis_ops.cache_channel_data = AsyncMock(return_value=True)
    redis_ops.cache_network_metrics = AsyncMock(return_value=True)
    return redis_ops

@pytest.fixture
def scraper(mock_redis_ops):
    """Fixture pour le scraper Amboss"""
    return AmbossScraper(mock_redis_ops)

@pytest.fixture
def sample_node_html():
    """HTML de test pour une page de nœud"""
    return """
    <html>
        <h1 class="node-alias">Test Node</h1>
        <div class="node-capacity">1.5 BTC</div>
        <div class="node-channels">10 channels</div>
        <div class="node-reputation">95.5</div>
    </html>
    """

@pytest.fixture
def sample_channel_html():
    """HTML de test pour une page de canal"""
    return """
    <html>
        <div class="channel-capacity">0.1 BTC</div>
        <div class="channel-fees">Base: 1000 Rate: 0.0001</div>
        <div class="channel-balance">Local: 0.05 Remote: 0.05</div>
        <div class="channel-age">30 days</div>
    </html>
    """

@pytest.fixture
def sample_network_html():
    """HTML de test pour une page réseau"""
    return """
    <html>
        <div class="network-capacity">1000 BTC</div>
        <div class="network-channels">50000 channels</div>
        <div class="network-nodes">10000 nodes</div>
        <div class="network-fees">0.0001</div>
    </html>
    """

@pytest.mark.asyncio
async def test_scrape_node_data(scraper, sample_node_html):
    """Test de l'extraction des données d'un nœud"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value=sample_node_html)
        
        node_data = await scraper.scrape_node_data("test_node_id")
        
        assert isinstance(node_data, NodeData)
        assert node_data.node_id == "test_node_id"
        assert node_data.alias == "Test Node"
        assert node_data.capacity == 150_000_000  # 1.5 BTC en sats
        assert node_data.channel_count == 10
        assert node_data.reputation_score == 95.5

@pytest.mark.asyncio
async def test_scrape_channel_data(scraper, sample_channel_html):
    """Test de l'extraction des données d'un canal"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value=sample_channel_html)
        
        channel_data = await scraper.scrape_channel_data("test_channel_id")
        
        assert isinstance(channel_data, ChannelData)
        assert channel_data.channel_id == "test_channel_id"
        assert channel_data.capacity == 10_000_000  # 0.1 BTC en sats
        assert channel_data.fee_rate == {"base_fee": 1000.0, "fee_rate": 0.0001}
        assert channel_data.balance == {"local": 0.05, "remote": 0.05}
        assert channel_data.age == 30

@pytest.mark.asyncio
async def test_scrape_network_metrics(scraper, sample_network_html):
    """Test de l'extraction des métriques réseau"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value=sample_network_html)
        
        metrics = await scraper.scrape_network_metrics()
        
        assert isinstance(metrics, NetworkMetrics)
        assert metrics.total_capacity == 100_000_000_000  # 1000 BTC en sats
        assert metrics.total_channels == 50000
        assert metrics.total_nodes == 10000
        assert metrics.average_fee_rate == 0.0001

@pytest.mark.asyncio
async def test_get_main_nodes(scraper):
    """Test de la récupération des nœuds principaux"""
    test_html = """
    <html>
        <div class="node-item" data-node-id="node1"></div>
        <div class="node-item" data-node-id="node2"></div>
    </html>
    """
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value=test_html)
        
        nodes = await scraper._get_main_nodes()
        
        assert len(nodes) == 2
        assert "node1" in nodes
        assert "node2" in nodes

@pytest.mark.asyncio
async def test_get_node_channels(scraper):
    """Test de la récupération des canaux d'un nœud"""
    test_html = """
    <html>
        <div class="channel-item" data-channel-id="channel1"></div>
        <div class="channel-item" data-channel-id="channel2"></div>
    </html>
    """
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(return_value=test_html)
        
        channels = await scraper._get_node_channels("test_node_id")
        
        assert len(channels) == 2
        assert "channel1" in channels
        assert "channel2" in channels

@pytest.mark.asyncio
async def test_update_all_data(scraper, sample_network_html, sample_node_html, sample_channel_html):
    """Test de la mise à jour complète des données"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        # Configuration des réponses mockées
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.text = AsyncMock(side_effect=[
            sample_network_html,  # Pour scrape_network_metrics
            "<html><div class='node-item' data-node-id='node1'></div></html>",  # Pour _get_main_nodes
            sample_node_html,  # Pour scrape_node_data
            "<html><div class='channel-item' data-channel-id='channel1'></div></html>",  # Pour _get_node_channels
            sample_channel_html  # Pour scrape_channel_data
        ])
        
        await scraper.update_all_data()
        
        # Vérification des appels à Redis
        assert scraper.redis_ops.cache_network_metrics.called
        assert scraper.redis_ops.cache_node_data.called
        assert scraper.redis_ops.cache_channel_data.called

@pytest.mark.asyncio
async def test_periodic_update(scraper):
    """Test de la mise à jour périodique"""
    with patch('asyncio.sleep') as mock_sleep:
        mock_sleep.side_effect = [None, Exception("Test stop")]
        
        with pytest.raises(Exception):
            await scraper.start_periodic_update(interval=1)
        
        assert mock_sleep.call_count == 2 