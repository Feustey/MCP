import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from lnplus_integration.client import LNPlusClient
from lnplus_integration.models import LightningSwap, SwapCreationRequest, NodeMetrics, Rating
from lnplus_integration.exceptions import (
    LNPlusError,
    LNPlusAuthError,
    LNPlusValidationError
)

@pytest.fixture
async def client():
    client = LNPlusClient()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_authentication(client):
    """Test du processus d'authentification"""
    with patch.object(client, '_get_message_to_sign') as mock_get_message, \
         patch.object(client, '_verify_signature') as mock_verify, \
         patch.object(client._lnbits, 'sign_message') as mock_sign:
        
        # Configurer les mocks
        mock_get_message.return_value = ("test-message", datetime.now() + timedelta(minutes=5))
        mock_sign.return_value = "test-signature"
        mock_verify.return_value = {
            "node_found": True,
            "pubkey": "test-pubkey"
        }
        
        # Exécuter l'authentification
        await client.ensure_connected()
        
        # Vérifier les appels
        mock_get_message.assert_called_once()
        mock_sign.assert_called_once_with("test-message")
        mock_verify.assert_called_once_with("test-message", "test-signature")
        assert client._auth_token == "test-pubkey"

@pytest.mark.asyncio
async def test_get_balance(client):
    """Test de la récupération du solde"""
    with patch.object(client._lnbits, 'get_balance') as mock_balance:
        mock_balance.return_value = 1000000  # 0.01 BTC
        
        balance = await client.get_balance()
        
        mock_balance.assert_called_once()
        assert balance == 1000000

@pytest.mark.asyncio
async def test_get_swaps(client):
    """Test de la récupération des swaps"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = {
            "swaps": [
                {"id": "1", "amount": 100000, "type": "inbound"},
                {"id": "2", "amount": 200000, "type": "outbound"}
            ]
        }
        
        swaps = await client.get_swaps(filters={"status": "pending"})
        
        mock_request.assert_called_once_with(
            "GET",
            "/swaps",
            params={"status": "pending"}
        )
        assert len(swaps) == 2
        assert isinstance(swaps[0], LightningSwap)

@pytest.mark.asyncio
async def test_create_swap(client):
    """Test de la création d'un swap"""
    with patch.object(client, '_make_request') as mock_request:
        swap_request = SwapCreationRequest(
            amount=100000,
            type="inbound"
        )
        mock_request.return_value = {
            "id": "1",
            "amount": 100000,
            "type": "inbound"
        }
        
        swap = await client.create_swap(swap_request)
        
        mock_request.assert_called_once_with(
            "POST",
            "/swaps",
            data=swap_request.dict()
        )
        assert isinstance(swap, LightningSwap)
        assert swap.amount == 100000

@pytest.mark.asyncio
async def test_get_node_metrics(client):
    """Test de la récupération des métriques d'un nœud"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = {
            "capacity": 1000000,
            "channels": 10
        }
        
        metrics = await client.get_node_metrics("test-node")
        
        mock_request.assert_called_once_with(
            "GET",
            "/nodes/test-node/metrics"
        )
        assert isinstance(metrics, NodeMetrics)

@pytest.mark.asyncio
async def test_get_node_rating(client):
    """Test de la récupération de la note d'un nœud"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = {
            "score": 4.5,
            "count": 10
        }
        
        rating = await client.get_node_rating("test-node")
        
        mock_request.assert_called_once_with(
            "GET",
            "/nodes/test-node/rating"
        )
        assert isinstance(rating, Rating)

@pytest.mark.asyncio
async def test_error_handling(client):
    """Test de la gestion des erreurs"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.side_effect = LNPlusError("Test error")
        
        with pytest.raises(LNPlusError):
            await client.get_swaps()

@pytest.mark.asyncio
async def test_validation_error(client):
    """Test de la gestion des erreurs de validation"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.side_effect = LNPlusValidationError("Invalid data")
        
        with pytest.raises(LNPlusValidationError):
            await client.create_swap(SwapCreationRequest(amount=-100, type="invalid"))

@pytest.mark.asyncio
async def test_auth_error(client):
    """Test de la gestion des erreurs d'authentification"""
    with patch.object(client, '_get_message_to_sign') as mock_get_message:
        mock_get_message.side_effect = LNPlusAuthError("Auth failed")
        
        with pytest.raises(LNPlusAuthError):
            await client.ensure_connected() 