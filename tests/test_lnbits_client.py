import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.lnbits_client import LNBitsClient, LNBitsClientError

@pytest.fixture
async def mock_client():
    """Fixture pour mocker le client HTTP"""
    with patch('httpx.AsyncClient') as mock:
        mock.return_value = AsyncMock()
        mock.return_value.request = AsyncMock()
        mock.return_value.aclose = AsyncMock()
        yield mock

@pytest.mark.asyncio
async def test_ensure_connected(mock_client):
    """Test de la connexion au client"""
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    assert client._client is not None
    mock_client.assert_called_once()

@pytest.mark.asyncio
async def test_get_local_node_info(mock_client):
    """Test de la récupération des informations du nœud local"""
    mock_response = {
        "alias": "test_node",
        "color": "#000000",
        "id": "test_id"
    }
    
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.json.return_value = mock_response
    mock_client.return_value.request.return_value.status_code = 200
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    result = await client.get_local_node_info()
    assert result == mock_response

@pytest.mark.asyncio
async def test_create_invoice(mock_client):
    """Test de la création d'une facture"""
    mock_response = {
        "payment_hash": "test_hash",
        "payment_request": "test_request"
    }
    
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.json.return_value = mock_response
    mock_client.return_value.request.return_value.status_code = 201
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    result = await client.create_invoice(amount=1000, memo="Test invoice")
    assert result == mock_response

@pytest.mark.asyncio
async def test_error_handling(mock_client):
    """Test de la gestion des erreurs"""
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.status_code = 500
    mock_client.return_value.request.return_value.text = "Internal Server Error"
    mock_client.return_value.request.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=AsyncMock(),
        response=AsyncMock(status_code=500, text="Internal Server Error")
    )
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    
    with pytest.raises(LNBitsClientError) as exc_info:
        await client.get_local_node_info()
    
    assert "500" in str(exc_info.value)
    assert "Internal Server Error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_pay_invoice(mock_client):
    """Test du paiement d'une facture"""
    mock_response = {
        "payment_hash": "test_payment_hash",
        "status": "complete"
    }
    
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.json.return_value = mock_response
    mock_client.return_value.request.return_value.status_code = 200
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    result = await client.pay_invoice(bolt11="test_invoice")
    assert result == mock_response

@pytest.mark.asyncio
async def test_get_transactions(mock_client):
    """Test de la récupération des transactions"""
    mock_response = {
        "transactions": [
            {
                "payment_hash": "hash1",
                "amount": 1000,
                "memo": "test1"
            },
            {
                "payment_hash": "hash2",
                "amount": 2000,
                "memo": "test2"
            }
        ]
    }
    
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.json.return_value = mock_response
    mock_client.return_value.request.return_value.status_code = 200
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    result = await client.get_transactions()
    assert result == mock_response

@pytest.mark.asyncio
async def test_get_wallet_info(mock_client):
    """Test de la récupération des informations du wallet"""
    mock_response = {
        "balance": 10000,
        "name": "test_wallet",
        "user": "test_user"
    }
    
    mock_client.return_value.request.return_value = AsyncMock()
    mock_client.return_value.request.return_value.json.return_value = mock_response
    mock_client.return_value.request.return_value.status_code = 200
    
    client = LNBitsClient(endpoint="http://test.lnbits", api_key="test_key")
    await client.ensure_connected()
    result = await client.get_wallet_info()
    assert result == mock_response

@pytest.mark.asyncio
async def test_connection_timeout(mock_client):
    """Test du timeout de connexion"""
    mock_client.return_value.request.side_effect = httpx.TimeoutException("Connection timeout")
    
    with pytest.raises(LNBitsClientError) as exc_info:
        client = LNBitsClient(endpoint="http://invalid.url", api_key="test_key")
        await client.ensure_connected()
    
    assert "Connection timeout" in str(exc_info.value) 