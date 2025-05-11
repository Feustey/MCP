"""
Tests pour le client LNBits principal
"""
import pytest
import json
import os
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from src.unified_clients.lnbits_client import (
    LNBitsClient,
    InvoiceResponse,
    PaymentResponse,
    WalletInfo
)
from src.unified_clients.lnbits_base_client import LNBitsError

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

class TestLNBitsClient:
    """Tests pour le client LNBits principal"""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture pour créer un client mock"""
        return LNBitsClient(
            url="https://test-lnbits.com",
            invoice_key="test_invoice_key",
            admin_key="test_admin_key"
        )
    
    @pytest.mark.asyncio
    async def test_get_wallet_details(self, mock_client):
        """Test de la récupération des détails du wallet"""
        wallet_response = load_mock_response("lnbits_wallet_response.json")
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = wallet_response
            
            result = await mock_client.get_wallet_details()
            
            assert isinstance(result, WalletInfo)
            assert result.id == wallet_response["id"]
            assert result.name == wallet_response["name"]
            assert result.balance == wallet_response["balance"]
            
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/wallet",
                use_admin_key=True
            )
    
    @pytest.mark.asyncio
    async def test_get_wallet_details_error(self, mock_client):
        """Test de la gestion des erreurs lors de la récupération des détails du wallet"""
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            with pytest.raises(LNBitsError) as excinfo:
                await mock_client.get_wallet_details()
            
            assert "Échec de récupération des détails du wallet" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_get_balance(self, mock_client):
        """Test de la récupération du solde"""
        wallet_response = load_mock_response("lnbits_wallet_response.json")
        
        with patch.object(mock_client, "get_wallet_details") as mock_get_wallet:
            mock_get_wallet.return_value = WalletInfo(**wallet_response)
            
            result = await mock_client.get_balance()
            
            assert result == wallet_response["balance"]
            mock_get_wallet.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_invoice(self, mock_client):
        """Test de la création d'une facture"""
        invoice_response = {
            "payment_hash": "test_hash",
            "payment_request": "lnbc500n...",
            "checking_id": "test_id",
            "lnurl_response": None
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = invoice_response
            
            result = await mock_client.create_invoice(
                amount=1000,
                memo="Test invoice"
            )
            
            assert isinstance(result, InvoiceResponse)
            assert result.payment_hash == invoice_response["payment_hash"]
            assert result.payment_request == invoice_response["payment_request"]
            
            mock_execute.assert_called_once_with(
                method="post",
                endpoint="api/v1/payments",
                use_admin_key=False,
                json_data={
                    "amount": 1000,
                    "memo": "Test invoice",
                    "expiry": 3600
                }
            )
    
    @pytest.mark.asyncio
    async def test_pay_invoice_success(self, mock_client):
        """Test du paiement d'une facture - réussi"""
        payment_response = {
            "payment_hash": "test_hash",
            "checking_id": "test_id",
            "fee": 10,
            "preimage": "test_preimage"
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = payment_response
            
            result = await mock_client.pay_invoice(
                bolt11="lnbc500n..."
            )
            
            assert isinstance(result, PaymentResponse)
            assert result.payment_hash == payment_response["payment_hash"]
            assert result.checking_id == payment_response["checking_id"]
            assert result.fee == payment_response["fee"]
            assert result.preimage == payment_response["preimage"]
            assert result.success is True
            
            mock_execute.assert_called_once_with(
                method="post",
                endpoint="api/v1/payments/bolt11",
                use_admin_key=True,
                json_data={
                    "bolt11": "lnbc500n..."
                }
            )
    
    @pytest.mark.asyncio
    async def test_pay_invoice_with_fee_limit(self, mock_client):
        """Test du paiement d'une facture avec limite de frais"""
        payment_response = {
            "payment_hash": "test_hash",
            "checking_id": "test_id",
            "fee": 5,
            "preimage": "test_preimage"
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = payment_response
            
            result = await mock_client.pay_invoice(
                bolt11="lnbc500n...",
                fee_limit_msat=1000
            )
            
            assert result.success is True
            
            mock_execute.assert_called_once_with(
                method="post",
                endpoint="api/v1/payments/bolt11",
                use_admin_key=True,
                json_data={
                    "bolt11": "lnbc500n...",
                    "fee_limit_msat": 1000
                }
            )
    
    @pytest.mark.asyncio
    async def test_pay_invoice_failure(self, mock_client):
        """Test du paiement d'une facture - échec"""
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = LNBitsError("Paiement échoué")
            
            result = await mock_client.pay_invoice(
                bolt11="lnbc500n..."
            )
            
            assert result.success is False
            assert "Paiement échoué" in result.error_message
    
    @pytest.mark.asyncio
    async def test_check_invoice_status_paid(self, mock_client):
        """Test de la vérification du statut d'une facture - payée"""
        check_response = {"paid": True}
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = check_response
            
            result = await mock_client.check_invoice_status("test_hash")
            
            assert result is True
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/payments/test_hash",
                use_admin_key=False
            )
    
    @pytest.mark.asyncio
    async def test_check_invoice_status_unpaid(self, mock_client):
        """Test de la vérification du statut d'une facture - non payée"""
        check_response = {"paid": False}
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = check_response
            
            result = await mock_client.check_invoice_status("test_hash")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_invoice_status_error(self, mock_client):
        """Test de la vérification du statut d'une facture - erreur"""
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            result = await mock_client.check_invoice_status("test_hash")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_payments(self, mock_client):
        """Test de la récupération des paiements"""
        payments_response = [
            {"id": "payment1", "amount": 1000, "fee": 1, "pending": False},
            {"id": "payment2", "amount": 2000, "fee": 2, "pending": True}
        ]
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = payments_response
            
            result = await mock_client.get_payments(limit=5, offset=10)
            
            assert result == payments_response
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/payments",
                use_admin_key=True,
                params={"limit": 5, "offset": 10}
            )
    
    @pytest.mark.asyncio
    async def test_decode_invoice(self, mock_client):
        """Test du décodage d'une facture"""
        decode_response = {
            "amount_msat": 1000000,
            "description": "Test invoice",
            "expiry": 3600,
            "timestamp": 1625097600
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = decode_response
            
            result = await mock_client.decode_invoice("lnbc500n...")
            
            assert result == decode_response
            mock_execute.assert_called_once_with(
                method="post",
                endpoint="api/v1/payments/decode",
                use_admin_key=False,
                json_data={"data": "lnbc500n..."}
            ) 