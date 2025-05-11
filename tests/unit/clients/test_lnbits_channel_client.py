"""
Tests pour le client LNBits de gestion des canaux
"""
import pytest
import json
import os
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

from src.unified_clients.lnbits_channel_client import (
    LNBitsChannelClient,
    ChannelPolicy
)
from src.unified_clients.lnbits_client import ChannelInfo
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

class TestLNBitsChannelClient:
    """Tests pour le client LNBits de gestion des canaux"""
    
    @pytest.fixture
    def mock_client(self):
        """Fixture pour créer un client mock"""
        return LNBitsChannelClient(
            url="https://test-lnbits.com",
            admin_key="test_admin_key"
        )
    
    @pytest.mark.asyncio
    async def test_list_channels(self, mock_client):
        """Test de la récupération des canaux"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = channels_response
            
            # Test avec tous les canaux
            channels = await mock_client.list_channels()
            
            assert len(channels) == 2
            assert isinstance(channels[0], ChannelInfo)
            assert channels[0].id == channels_response[0]["id"]
            assert channels[0].remote_pubkey == channels_response[0]["remote_pubkey"]
            
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/lnd/channels",
                use_admin_key=True
            )
    
    @pytest.mark.asyncio
    async def test_list_channels_active_only(self, mock_client):
        """Test de la récupération des canaux actifs uniquement"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = channels_response
            
            # Test avec canaux actifs uniquement
            active_channels = await mock_client.list_channels(active_only=True)
            
            assert len(active_channels) == 1
            assert active_channels[0].active is True
    
    @pytest.mark.asyncio
    async def test_list_channels_error(self, mock_client):
        """Test de la gestion des erreurs lors de la récupération des canaux"""
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            with pytest.raises(LNBitsError) as excinfo:
                await mock_client.list_channels()
            
            assert "Échec de récupération des canaux" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_get_channel_by_id(self, mock_client):
        """Test de la récupération d'un canal par ID"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        
        with patch.object(mock_client, "list_channels") as mock_list:
            # Convertir les dictionnaires en objets ChannelInfo
            channel_objects = [ChannelInfo(**chan) for chan in channels_response]
            mock_list.return_value = channel_objects
            
            # Récupération par ID
            channel = await mock_client.get_channel("channel1")
            
            assert channel is not None
            assert channel.id == "channel1"
            mock_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_channel_by_short_id(self, mock_client):
        """Test de la récupération d'un canal par short_id"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        
        with patch.object(mock_client, "list_channels") as mock_list:
            # Convertir les dictionnaires en objets ChannelInfo
            channel_objects = [ChannelInfo(**chan) for chan in channels_response]
            mock_list.return_value = channel_objects
            
            # Récupération par short_id
            channel = await mock_client.get_channel("123x456x1")
            
            assert channel is not None
            assert channel.short_id == "123x456x1"
    
    @pytest.mark.asyncio
    async def test_get_channel_not_found(self, mock_client):
        """Test de la récupération d'un canal inexistant"""
        with patch.object(mock_client, "list_channels") as mock_list:
            mock_list.return_value = []
            
            channel = await mock_client.get_channel("non_existent")
            
            assert channel is None
    
    @pytest.mark.asyncio
    async def test_get_forwarding_history(self, mock_client):
        """Test de la récupération de l'historique de forwarding"""
        forwarding_response = [
            {"timestamp": "2025-05-10", "in_channel": "channel1", "out_channel": "channel2", "amount": 1000, "fee": 1},
            {"timestamp": "2025-05-11", "in_channel": "channel2", "out_channel": "channel1", "amount": 2000, "fee": 2}
        ]
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = forwarding_response
            
            result = await mock_client.get_forwarding_history(
                start_date="2025-05-01",
                end_date="2025-05-15",
                limit=10
            )
            
            assert result == forwarding_response
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/lnd/forwarding/history",
                use_admin_key=True,
                params={
                    "limit": 10,
                    "offset": 0,
                    "start_date": "2025-05-01",
                    "end_date": "2025-05-15"
                }
            )
    
    @pytest.mark.asyncio
    async def test_update_channel_policy(self, mock_client):
        """Test de la mise à jour de la politique d'un canal"""
        policy_response = {"success": True, "message": "Policy updated"}
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = policy_response
            
            policy = ChannelPolicy(
                base_fee_msat=2000,
                fee_rate_ppm=500,
                time_lock_delta=40,
                min_htlc_msat=1000,
                disabled=False
            )
            
            result = await mock_client.update_channel_policy(
                channel_point="txid1:0",
                policy=policy
            )
            
            assert result is True
            mock_execute.assert_called_once_with(
                method="post",
                endpoint="api/v1/lnd/channel/policy",
                use_admin_key=True,
                json_data={
                    "channel_point": "txid1:0",
                    "base_fee_msat": 2000,
                    "fee_rate_ppm": 500,
                    "time_lock_delta": 40,
                    "min_htlc_msat": 1000,
                    "disabled": False
                }
            )
    
    @pytest.mark.asyncio
    async def test_update_channel_policy_with_target_node(self, mock_client):
        """Test de la mise à jour de la politique d'un canal avec nœud cible"""
        policy_response = {"success": True}
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = policy_response
            
            policy = ChannelPolicy(base_fee_msat=3000, fee_rate_ppm=600)
            
            result = await mock_client.update_channel_policy(
                channel_point="txid1:0",
                policy=policy,
                target_node="02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
            )
            
            assert result is True
            
            expected_data = {
                "channel_point": "txid1:0",
                "base_fee_msat": 3000,
                "fee_rate_ppm": 600,
                "time_lock_delta": 40,
                "disabled": False,
                "target_node": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
            }
            
            # Vérifier que les données ont été correctement passées
            mock_execute.assert_called_once()
            actual_data = mock_execute.call_args[1]["json_data"]
            assert actual_data == expected_data
    
    @pytest.mark.asyncio
    async def test_update_channel_policy_failure(self, mock_client):
        """Test de la mise à jour de la politique d'un canal - échec"""
        policy_response = {"success": False, "message": "Channel not found"}
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = policy_response
            
            policy = ChannelPolicy()
            result = await mock_client.update_channel_policy("txid1:0", policy)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_channel_balances(self, mock_client):
        """Test de la récupération des soldes des canaux"""
        balances_response = {
            "total_balance": 5000000,
            "confirmed_balance": 4900000,
            "unconfirmed_balance": 100000,
            "pending_open_balance": 0
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = balances_response
            
            result = await mock_client.get_channel_balances()
            
            assert result["total_balance"] == balances_response["total_balance"]
            assert result["confirmed_balance"] == balances_response["confirmed_balance"]
            
            mock_execute.assert_called_once_with(
                method="get",
                endpoint="api/v1/lnd/balance/channels",
                use_admin_key=True
            )
    
    @pytest.mark.asyncio
    async def test_get_node_info(self, mock_client):
        """Test de la récupération des informations d'un nœud"""
        node_response = {
            "alias": "TestNode",
            "color": "#ff9900",
            "features": {},
            "last_update": 1622548800,
            "pub_key": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
        }
        
        with patch.object(mock_client, "_execute_with_retry") as mock_execute:
            mock_execute.return_value = node_response
            
            pubkey = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
            result = await mock_client.get_node_info(pubkey)
            
            assert result == node_response
            mock_execute.assert_called_once_with(
                method="get",
                endpoint=f"api/v1/lnd/node/{pubkey}",
                use_admin_key=True
            )
    
    @pytest.mark.asyncio
    async def test_update_all_channel_fees(self, mock_client):
        """Test de la mise à jour globale des frais des canaux"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        
        # Simuler la liste des canaux retournée
        channel_objects = [ChannelInfo(**chan) for chan in channels_response]
        
        with patch.object(mock_client, "list_channels") as mock_list, \
             patch.object(mock_client, "update_channel_policy") as mock_update:
            
            mock_list.return_value = channel_objects
            # Premier canal réussi, deuxième échec
            mock_update.side_effect = [True, False]
            
            result = await mock_client.update_all_channel_fees(
                base_fee_msat=1500,
                fee_rate_ppm=750
            )
            
            # Vérifier que seul le canal actif a été mis à jour
            assert "txid1:0" in result
            assert result["txid1:0"] is True
            
            # Le canal inactif n'a pas dû être traité (car on n'a pas appelé mock_update une 2e fois)
            assert mock_update.call_count == 1
            
            # Vérifier que la politique a été correctement passée
            mock_update.assert_called_once()
            _, kwargs = mock_update.call_args
            policy = kwargs["policy"]
            assert policy.base_fee_msat == 1500
            assert policy.fee_rate_ppm == 750
    
    @pytest.mark.asyncio
    async def test_update_all_channel_fees_with_exclusion(self, mock_client):
        """Test de la mise à jour globale des frais avec exclusion de certains canaux"""
        channels_response = load_mock_response("lnbits_channels_response.json")
        channel_objects = [ChannelInfo(**chan) for chan in channels_response]
        
        with patch.object(mock_client, "list_channels") as mock_list, \
             patch.object(mock_client, "update_channel_policy") as mock_update:
            
            mock_list.return_value = channel_objects
            mock_update.return_value = True
            
            # Exclure le premier canal
            result = await mock_client.update_all_channel_fees(
                base_fee_msat=1500,
                fee_rate_ppm=750,
                exclude_channels=["txid1:0"]
            )
            
            # Aucun canal n'a dû être mis à jour (le premier est exclu, le deuxième est inactif)
            assert not result
            assert mock_update.call_count == 0 