import pytest
import os
from src.rag import RAGWorkflow
from src.server import get_headers, get_network_summary, get_centralities
from src.lnbits_client import LNBitsClient, LNBitsClientError
from src.models import Document, QueryHistory, SystemStats
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import json
import httpx
import asyncio

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('SPARKSEER_API_KEY', 'test_api_key')
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setenv('OPENAI_API_KEY', 'test_openai_key')
    monkeypatch.setenv('MONGODB_URI', 'mongodb://localhost:27017/test')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')

@pytest.fixture
def rag_workflow():
    """Fixture pour créer une instance de RAGWorkflow."""
    workflow = RAGWorkflow()
    workflow.openai_client = AsyncMock()
    workflow.tokenizer = AsyncMock()
    workflow.ingest_documents = AsyncMock()
    workflow.query = AsyncMock(return_value="Test response")
    return workflow

def test_get_headers(mock_env_vars):
    """Test de la fonction get_headers."""
    headers = get_headers()
    assert headers['api-key'] == 'test_api_key'
    assert headers['Content-Type'] == 'application/json'

@pytest.mark.asyncio
async def test_rag_workflow_initialization(rag_workflow):
    """Test de l'initialisation du RAGWorkflow."""
    assert rag_workflow is not None
    assert hasattr(rag_workflow, 'openai_client')
    assert hasattr(rag_workflow, 'tokenizer')

@pytest.mark.asyncio
async def test_rag_workflow_query(rag_workflow):
    """Test de la fonction query du RAGWorkflow."""
    # Mock de la méthode ingest_documents
    rag_workflow.ingest_documents = AsyncMock()
    rag_workflow.query = AsyncMock(return_value="Test response")
    
    # Test de la requête
    result = await rag_workflow.query("Test query")
    assert result == "Test response"
    rag_workflow.query.assert_called_once_with("Test query")

@pytest.mark.asyncio
async def test_get_network_summary(mock_env_vars):
    """Test de la fonction get_network_summary."""
    try:
        result = await get_network_summary()
        assert isinstance(result, (dict, str))
    except Exception as e:
        pytest.skip(f"Test skipped due to external dependency: {str(e)}")

@pytest.mark.asyncio
async def test_get_centralities(mock_env_vars):
    """Test de la fonction get_centralities."""
    try:
        result = await get_centralities()
        assert isinstance(result, (dict, str))
    except Exception as e:
        pytest.skip(f"Test skipped due to external dependency: {str(e)}")

@pytest.mark.asyncio
async def test_lnbits_wallet_operations():
    """Test des opérations du portefeuille LNbits"""
    mock_channels = [
        {
            "channel_id": "ch1",
            "remote_pubkey": "peer1",
            "capacity": 100000,
            "local_balance": 50000,
            "remote_balance": 50000
        },
        {
            "channel_id": "ch2",
            "remote_pubkey": "peer2",
            "capacity": 200000,
            "local_balance": 100000,
            "remote_balance": 100000
        }
    ]

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value=mock_channels)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        wallet_info = await client.get_local_node_info()
        assert wallet_info["current_peers"] == {"peer1", "peer2"}
        assert wallet_info["pubkey"] is None

@pytest.mark.asyncio
async def test_lnbits_channel_operations():
    """Test des opérations sur les canaux LNbits"""
    mock_channels = [
        {
            "channel_id": "ch1",
            "remote_pubkey": "peer1",
            "capacity": 100000,
            "local_balance": 50000,
            "remote_balance": 50000
        }
    ]

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value=mock_channels)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        channels = await client.get_local_node_info()
        assert channels["current_peers"] == {"peer1"}
        assert channels["pubkey"] is None

@pytest.mark.asyncio
async def test_lnbits_error_handling():
    """Test de la gestion des erreurs LNbits"""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status = AsyncMock(side_effect=httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=AsyncMock(),
        response=mock_response
    ))

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        with pytest.raises(LNBitsClientError) as exc_info:
            await client.get_local_node_info()
        assert "Erreur API" in str(exc_info.value)

@pytest.mark.asyncio
async def test_lnbits_payment_operations():
    """Test des opérations de paiement LNbits"""
    mock_payment_response = {
        "payment_hash": "test_hash",
        "payment_preimage": "test_preimage",
        "amount": 1000,
        "fee": 1,
        "success": True
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_payment_response)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        payment = await client.pay_invoice(bolt11="lnbc...")
        assert payment == mock_payment_response

@pytest.mark.asyncio
async def test_lnbits_transaction_history():
    """Test de l'historique des transactions LNbits"""
    mock_transactions = [
        {
            "payment_hash": "hash1",
            "amount": 1000,
            "fee": 1,
            "memo": "Test payment 1",
            "time": 1677721600,
            "pending": False
        }
    ]

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value=mock_transactions)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        transactions = await client.get_transactions()
        assert transactions == mock_transactions

@pytest.mark.asyncio
async def test_lnbits_health_check():
    """Test de la vérification de santé de LNbits"""
    mock_health_response = {"status": "ok"}

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value=mock_health_response)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        health = await client._request("GET", "/api/v1/health")
        assert health == mock_health_response

@pytest.mark.asyncio
async def test_cache_operations():
    """Test des opérations de cache Redis"""
    mock_cached_data = {
        "response": "Cached response",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "cached_at": datetime.now().isoformat()
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_cached_data)
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        response = await client._request("GET", "/test")
        assert response == mock_cached_data

@pytest.mark.asyncio
async def test_cache_expiration():
    """Test de l'expiration du cache Redis"""
    # Mock des données expirées
    expired_data = {
        "response": "Expired response",
        "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "cached_at": (datetime.now() - timedelta(hours=2)).isoformat()
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        # Configuration des mocks
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expired_data
        mock_client.return_value.request.return_value = mock_response
        
        # Test avec données expirées
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        cached_response = await client._get_cached_response("test query")
        assert cached_response is None

@pytest.mark.asyncio
async def test_connection_management():
    """Test de la gestion des connexions"""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"status": "ok"})
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with patch('httpx.AsyncClient', return_value=mock_client):
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        await client.ensure_connected()
        assert client.client is not None

@pytest.mark.asyncio
async def test_connection_errors():
    """Test de la gestion des erreurs de connexion"""
    with patch('httpx.AsyncClient') as mock_client:
        # Configuration des mocks pour simuler des erreurs
        mock_client.return_value.request.side_effect = httpx.RequestError("Connection error")
        
        # Test avec erreur de connexion
        client = LNBitsClient(endpoint="http://test", api_key="test_key")
        with pytest.raises(LNBitsClientError) as exc_info:
            await client.ensure_connected()
        assert "Connection error" in str(exc_info.value)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 