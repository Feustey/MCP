"""
Tests pour le client LNBits de base
"""
import pytest
import json
import httpx
import asyncio
import os
from typing import Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock

from src.unified_clients.lnbits_base_client import (
    LNBitsBaseClient,
    LNBitsError,
    LNBitsErrorType,
    RetryConfig
)

# Charger les réponses de test
def load_mock_response(filename: str) -> Dict[str, Any]:
    """Charge une réponse mock à partir d'un fichier JSON"""
    file_path = os.path.join(
        os.path.dirname(__file__), 
        "mock_responses", 
        filename
    )
    with open(file_path, 'r') as f:
        return json.load(f)

class TestLNBitsBaseClient:
    """Tests pour le client LNBits de base"""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture pour créer un client mock"""
        return LNBitsBaseClient(
            url="https://test-lnbits.com",
            invoice_key="test_invoice_key",
            admin_key="test_admin_key"
        )
    
    def test_init(self):
        """Test de l'initialisation du client"""
        client = LNBitsBaseClient(
            url="https://test-lnbits.com",
            invoice_key="test_invoice_key",
            admin_key="test_admin_key"
        )
        
        assert client.url == "https://test-lnbits.com"
        assert client.invoice_key == "test_invoice_key"
        assert client.admin_key == "test_admin_key"
    
    def test_init_url_trailing_slash(self):
        """Test de l'initialisation avec une URL se terminant par un slash"""
        client = LNBitsBaseClient(
            url="https://test-lnbits.com/",
            invoice_key="test_invoice_key"
        )
        
        assert client.url == "https://test-lnbits.com"
    
    def test_init_missing_url(self):
        """Test de l'initialisation avec une URL manquante"""
        with pytest.raises(ValueError, match="L'URL de l'API LNBits est obligatoire"):
            LNBitsBaseClient(url="", invoice_key="test_key")
    
    def test_get_headers_invoice(self, mock_client):
        """Test de la création des en-têtes pour la clé invoice"""
        headers = mock_client._get_headers(use_admin_key=False)
        
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Api-Key"] == "test_invoice_key"
    
    def test_get_headers_admin(self, mock_client):
        """Test de la création des en-têtes pour la clé admin"""
        headers = mock_client._get_headers(use_admin_key=True)
        
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Api-Key"] == "test_admin_key"
    
    def test_get_headers_missing_invoice_key(self):
        """Test de la création des en-têtes avec clé invoice manquante"""
        client = LNBitsBaseClient(url="https://test-lnbits.com", admin_key="admin_key")
        
        with pytest.raises(LNBitsError) as excinfo:
            client._get_headers(use_admin_key=False)
        
        assert excinfo.value.error_type == LNBitsErrorType.AUTHENTICATION_ERROR
    
    def test_get_headers_missing_admin_key(self):
        """Test de la création des en-têtes avec clé admin manquante"""
        client = LNBitsBaseClient(url="https://test-lnbits.com", invoice_key="invoice_key")
        
        with pytest.raises(LNBitsError) as excinfo:
            client._get_headers(use_admin_key=True)
        
        assert excinfo.value.error_type == LNBitsErrorType.AUTHENTICATION_ERROR
    
    def test_determine_error_type(self, mock_client):
        """Test de la détermination du type d'erreur"""
        # Créer des objets réponse mock
        auth_response = MagicMock()
        auth_response.status_code = 401
        
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        
        server_response = MagicMock()
        server_response.status_code = 500
        
        request_response = MagicMock()
        request_response.status_code = 400
        
        # Vérifier les types d'erreur
        assert mock_client._determine_error_type(auth_response) == LNBitsErrorType.AUTHENTICATION_ERROR
        assert mock_client._determine_error_type(rate_limit_response) == LNBitsErrorType.RATE_LIMIT_ERROR
        assert mock_client._determine_error_type(server_response) == LNBitsErrorType.SERVER_ERROR
        assert mock_client._determine_error_type(request_response) == LNBitsErrorType.REQUEST_ERROR
    
    @pytest.mark.asyncio
    async def test_check_connection_success(self):
        """Test de la vérification de connexion - succès"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            client = LNBitsBaseClient(url="https://test-lnbits.com")
            result = await client.check_connection()
            
            assert result is True
            mock_get.assert_called_once_with("https://test-lnbits.com/health")
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(self):
        """Test de la vérification de connexion - échec"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            
            client = LNBitsBaseClient(url="https://test-lnbits.com")
            result = await client.check_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, mock_client):
        """Test de l'exécution d'une requête avec succès"""
        expected_response = {"success": True, "data": "test"}
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_response
            mock_get.return_value = mock_response
            
            result = await mock_client._execute_with_retry(
                method="get",
                endpoint="test/endpoint"
            )
            
            assert result == expected_response
            mock_get.assert_called_once_with(
                "https://test-lnbits.com/test/endpoint",
                headers=mock_client._get_headers(use_admin_key=False),
                params=None
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_retry_server_error(self, mock_client):
        """Test de l'exécution d'une requête avec retry sur erreur serveur"""
        expected_response = {"success": True, "data": "test"}
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # Premier appel : erreur serveur
            error_response = AsyncMock()
            error_response.status_code = 500
            error_response.text = "Server error"
            
            # Deuxième appel : succès
            success_response = AsyncMock()
            success_response.status_code = 200
            success_response.json.return_value = expected_response
            
            mock_get.side_effect = [error_response, success_response]
            
            # Configurer un délai de retry plus court pour le test
            mock_client.retry_config = RetryConfig(base_delay=0.01)
            
            result = await mock_client._execute_with_retry(
                method="get",
                endpoint="test/endpoint"
            )
            
            assert result == expected_response
            assert mock_get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_max_attempts(self, mock_client):
        """Test de l'exécution d'une requête atteignant le nombre maximum de tentatives"""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Toujours échouer avec une erreur serveur
            error_response = AsyncMock()
            error_response.status_code = 500
            error_response.text = "Server error"
            mock_get.return_value = error_response
            
            # Configurer un délai de retry plus court pour le test et limiter à 2 tentatives
            mock_client.retry_config = RetryConfig(base_delay=0.01, max_attempts=2)
            
            with pytest.raises(LNBitsError) as excinfo:
                await mock_client._execute_with_retry(
                    method="get",
                    endpoint="test/endpoint"
                )
            
            assert excinfo.value.error_type == LNBitsErrorType.SERVER_ERROR
            assert mock_get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_close(self, mock_client):
        """Test de la fermeture du client"""
        with patch.object(mock_client.client, "aclose") as mock_aclose:
            await mock_client.close()
            mock_aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test de l'utilisation comme gestionnaire de contexte asynchrone"""
        client = LNBitsBaseClient(url="https://test-lnbits.com")
        
        with patch.object(client.client, "aclose") as mock_aclose:
            async with client as c:
                assert c is client
            
            mock_aclose.assert_called_once() 