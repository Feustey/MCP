import pytest
from unittest.mock import patch, MagicMock
import asyncio
from src.scanners.liquidity_scanner import LiquidityScanner, scan_channel_liquidity, analyze_liquidity_distribution

# Données de test
test_channels = [
    {
        "channel_id": "123x456x0",
        "capacity": 5000000,
        "local_balance": 2500000,
        "remote_balance": 2500000
    },
    {
        "channel_id": "789x012x0",
        "capacity": 8000000,
        "local_balance": 7000000,
        "remote_balance": 1000000
    }
]

@pytest.fixture
def mock_lnd_client():
    """Mock du client LND."""
    mock_client = MagicMock()
    mock_client.get_channel_balance.return_value = {
        "local_balance": {
            "sat": 10000000
        },
        "remote_balance": {
            "sat": 5000000
        }
    }
    mock_client.list_channels.return_value = {
        "channels": [
            {
                "chan_id": "123x456x0",
                "capacity": "5000000",
                "local_balance": "2500000",
                "remote_balance": "2500000",
                "active": True
            },
            {
                "chan_id": "789x012x0",
                "capacity": "8000000",
                "local_balance": "7000000",
                "remote_balance": "1000000",
                "active": True
            }
        ]
    }
    return mock_client

@pytest.mark.asyncio
async def test_scan_channel_liquidity(mock_lnd_client):
    """Test du scan de liquidité pour un canal."""
    # Configure le mock
    mock_lnd_client.get_channel_info.return_value = {
        "channel_id": "123x456x0",
        "capacity": "5000000",
        "local_balance": "2500000",
        "remote_balance": "2500000"
    }
    
    result = await scan_channel_liquidity(mock_lnd_client, "123x456x0")
    
    assert result["channel_id"] == "123x456x0"
    assert result["capacity"] == 5000000
    assert result["local_balance"] == 2500000
    assert result["remote_balance"] == 2500000
    assert "balance_ratio" in result
    assert result["balance_ratio"] == 0.5  # Devrait être équilibré

@pytest.mark.asyncio
async def test_scan_channel_liquidity_error(mock_lnd_client):
    """Test du scan de liquidité avec erreur."""
    # Configure le mock pour simuler une erreur
    mock_lnd_client.get_channel_info.side_effect = Exception("API Error")
    
    result = await scan_channel_liquidity(mock_lnd_client, "invalid-channel")
    
    assert result["channel_id"] == "invalid-channel"
    assert "error" in result
    assert "API Error" in result["error"]

def test_analyze_liquidity_distribution():
    """Test de l'analyse de la distribution de liquidité."""
    analysis = analyze_liquidity_distribution(test_channels)
    
    assert "total_capacity" in analysis
    assert analysis["total_capacity"] == 13000000
    assert "total_local_balance" in analysis
    assert analysis["total_local_balance"] == 9500000
    assert "total_remote_balance" in analysis
    assert analysis["total_remote_balance"] == 3500000
    assert "overall_balance_ratio" in analysis
    assert analysis["overall_balance_ratio"] == round(9500000 / 13000000, 2)
    assert "channel_imbalances" in analysis
    assert len(analysis["channel_imbalances"]) == 2

class TestLiquidityScanner:
    
    @pytest.mark.asyncio
    @patch('src.scanners.liquidity_scanner.create_lnd_client')
    async def test_scanner_init(self, mock_create_client):
        """Test de l'initialisation du scanner."""
        mock_create_client.return_value = MagicMock()
        
        scanner = LiquidityScanner("macaroon_path", "cert_path", "host:port")
        
        assert scanner.macaroon_path == "macaroon_path"
        assert scanner.tls_cert_path == "cert_path"
        assert scanner.lnd_host == "host:port"
        assert scanner.client is not None
        
    @pytest.mark.asyncio
    @patch('src.scanners.liquidity_scanner.scan_channel_liquidity')
    async def test_scan_all_channels(self, mock_scan_channel, mock_lnd_client):
        """Test du scan de tous les canaux."""
        # Configure le mock
        scanner = LiquidityScanner("macaroon_path", "cert_path", "host:port")
        scanner.client = mock_lnd_client
        
        # Configure le mock pour scan_channel_liquidity
        mock_scan_channel.side_effect = [
            {"channel_id": "123x456x0", "capacity": 5000000, "local_balance": 2500000, "remote_balance": 2500000, "balance_ratio": 0.5},
            {"channel_id": "789x012x0", "capacity": 8000000, "local_balance": 7000000, "remote_balance": 1000000, "balance_ratio": 0.875}
        ]
        
        results = await scanner.scan_all_channels()
        
        assert len(results) == 2
        assert mock_scan_channel.call_count == 2
        assert results[0]["channel_id"] == "123x456x0"
        assert results[1]["channel_id"] == "789x012x0"
        
    @pytest.mark.asyncio
    async def test_analyze_node_liquidity(self, mock_lnd_client):
        """Test de l'analyse de la liquidité du nœud."""
        scanner = LiquidityScanner("macaroon_path", "cert_path", "host:port")
        scanner.client = mock_lnd_client
        
        analysis = await scanner.analyze_node_liquidity()
        
        assert "total_capacity" in analysis
        assert "total_local_balance" in analysis
        assert "total_remote_balance" in analysis
        assert "overall_balance_ratio" in analysis
        assert "channel_count" in analysis
        assert analysis["channel_count"] == 2 