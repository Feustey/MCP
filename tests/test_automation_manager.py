import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import datetime
from src.automation_manager import AutomationManager

@pytest.fixture
def automation_manager():
    """Fixture pour l'instance de AutomationManager"""
    return AutomationManager(lncli_path="mock_lncli", rebalance_lnd_path="mock_rebalance_lnd")

@pytest.fixture
def lnbits_automation_manager():
    """Fixture pour l'instance de AutomationManager avec LNbits"""
    return AutomationManager(
        lncli_path="mock_lncli", 
        rebalance_lnd_path="mock_rebalance_lnd",
        lnbits_url="https://testnet.lnbits.com",
        lnbits_api_key="test_api_key",
        use_lnbits=True
    )

@pytest.mark.asyncio
async def test_update_fee_rate_success(automation_manager):
    """Test de la mise à jour des frais avec succès"""
    # Configuration du mock pour simuler un processus réussi
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour 0 (succès)
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.update_fee_rate("test_channel", 1000, 0.0001)
        
        # Vérifications
        assert result["success"] is True
        assert "Frais mis à jour avec succès" in result["message"]
        assert len(automation_manager.automation_history) == 1
        assert automation_manager.automation_history[0]["type"] == "fee_update"
        assert automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert automation_manager.automation_history[0]["success"] is True
        assert automation_manager.automation_history[0]["backend"] == "lncli"

@pytest.mark.asyncio
async def test_update_fee_rate_failure(automation_manager):
    """Test de la mise à jour des frais avec échec"""
    # Configuration du mock pour simuler un processus échoué
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour non nul (échec)
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: Invalid channel ID"))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.update_fee_rate("invalid_channel", 1000, 0.0001)
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors de la mise à jour des frais" in result["message"]
        assert len(automation_manager.automation_history) == 1
        assert automation_manager.automation_history[0]["type"] == "fee_update"
        assert automation_manager.automation_history[0]["channel_id"] == "invalid_channel"
        assert automation_manager.automation_history[0]["success"] is False
        assert automation_manager.automation_history[0]["backend"] == "lncli"

@pytest.mark.asyncio
async def test_update_fee_rate_lnbits_success(lnbits_automation_manager):
    """Test de la mise à jour des frais via LNbits avec succès"""
    # Configuration du mock pour simuler une requête HTTP réussie
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Configuration du mock pour retourner un statut 200 (succès)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "success"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.update_fee_rate("test_channel", 1000, 0.0001)
        
        # Vérifications
        assert result["success"] is True
        assert "Frais mis à jour avec succès" in result["message"]
        assert len(lnbits_automation_manager.automation_history) == 1
        assert lnbits_automation_manager.automation_history[0]["type"] == "fee_update"
        assert lnbits_automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert lnbits_automation_manager.automation_history[0]["success"] is True
        assert lnbits_automation_manager.automation_history[0]["backend"] == "lnbits"
        
        # Vérification de l'appel à l'API
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert "headers" in call_args
        assert call_args["headers"]["X-Api-Key"] == "test_api_key"
        assert "json" in call_args
        assert call_args["json"]["base_fee_msat"] == 1000
        assert call_args["json"]["fee_rate"] == 0.00001  # 0.0001 ppm = 0.00001%

@pytest.mark.asyncio
async def test_update_fee_rate_lnbits_failure(lnbits_automation_manager):
    """Test de la mise à jour des frais via LNbits avec échec"""
    # Configuration du mock pour simuler une requête HTTP échouée
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Configuration du mock pour retourner un statut 400 (échec)
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"detail": "Invalid channel ID"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.update_fee_rate("invalid_channel", 1000, 0.0001)
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors de la mise à jour des frais via LNbits" in result["message"]
        assert len(lnbits_automation_manager.automation_history) == 1
        assert lnbits_automation_manager.automation_history[0]["type"] == "fee_update"
        assert lnbits_automation_manager.automation_history[0]["channel_id"] == "invalid_channel"
        assert lnbits_automation_manager.automation_history[0]["success"] is False
        assert lnbits_automation_manager.automation_history[0]["backend"] == "lnbits"

@pytest.mark.asyncio
async def test_rebalance_channel_success(automation_manager):
    """Test du rééquilibrage de canal avec succès"""
    # Configuration du mock pour simuler un processus réussi
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour 0 (succès)
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Rebalance successful", b""))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.rebalance_channel("test_channel", 1000000, "outgoing")
        
        # Vérifications
        assert result["success"] is True
        assert "Rééquilibrage réussi" in result["message"]
        assert len(automation_manager.automation_history) == 1
        assert automation_manager.automation_history[0]["type"] == "rebalance"
        assert automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert automation_manager.automation_history[0]["amount"] == 1000000
        assert automation_manager.automation_history[0]["direction"] == "outgoing"
        assert automation_manager.automation_history[0]["success"] is True
        assert automation_manager.automation_history[0]["backend"] == "rebalance-lnd"

@pytest.mark.asyncio
async def test_rebalance_channel_failure(automation_manager):
    """Test du rééquilibrage de canal avec échec"""
    # Configuration du mock pour simuler un processus échoué
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour non nul (échec)
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: Insufficient funds"))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.rebalance_channel("test_channel", 1000000, "outgoing")
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors du rééquilibrage" in result["message"]
        assert len(automation_manager.automation_history) == 1
        assert automation_manager.automation_history[0]["type"] == "rebalance"
        assert automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert automation_manager.automation_history[0]["success"] is False
        assert automation_manager.automation_history[0]["backend"] == "rebalance-lnd"

@pytest.mark.asyncio
async def test_rebalance_channel_lnbits_success(lnbits_automation_manager):
    """Test du rééquilibrage de canal via LNbits avec succès"""
    # Configuration du mock pour simuler une requête HTTP réussie
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Configuration du mock pour retourner un statut 200 (succès)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "success", "txid": "123456"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.rebalance_channel("test_channel", 1000000, "outgoing")
        
        # Vérifications
        assert result["success"] is True
        assert "Rééquilibrage réussi" in result["message"]
        assert len(lnbits_automation_manager.automation_history) == 1
        assert lnbits_automation_manager.automation_history[0]["type"] == "rebalance"
        assert lnbits_automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert lnbits_automation_manager.automation_history[0]["amount"] == 1000000
        assert lnbits_automation_manager.automation_history[0]["direction"] == "outgoing"
        assert lnbits_automation_manager.automation_history[0]["success"] is True
        assert lnbits_automation_manager.automation_history[0]["backend"] == "lnbits"
        
        # Vérification de l'appel à l'API
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert "headers" in call_args
        assert call_args["headers"]["X-Api-Key"] == "test_api_key"
        assert "json" in call_args
        assert call_args["json"]["amount"] == 1000000
        assert call_args["json"]["direction"] == "outgoing"

@pytest.mark.asyncio
async def test_rebalance_channel_lnbits_failure(lnbits_automation_manager):
    """Test du rééquilibrage de canal via LNbits avec échec"""
    # Configuration du mock pour simuler une requête HTTP échouée
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Configuration du mock pour retourner un statut 400 (échec)
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"detail": "Insufficient funds"})
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.rebalance_channel("test_channel", 1000000, "outgoing")
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors du rééquilibrage via LNbits" in result["message"]
        assert len(lnbits_automation_manager.automation_history) == 1
        assert lnbits_automation_manager.automation_history[0]["type"] == "rebalance"
        assert lnbits_automation_manager.automation_history[0]["channel_id"] == "test_channel"
        assert lnbits_automation_manager.automation_history[0]["success"] is False
        assert lnbits_automation_manager.automation_history[0]["backend"] == "lnbits"

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_success(automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée avec succès"""
    # Configuration du mock pour simuler un processus réussi pour getchaninfo
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour 0 (succès) pour getchaninfo
        mock_process = MagicMock()
        mock_process.returncode = 0
        channel_info = {
            "capacity": 10000000,
            "local_balance": 8000000
        }
        mock_process.communicate = AsyncMock(return_value=(json.dumps(channel_info).encode(), b""))
        mock_exec.return_value = mock_process
        
        # Configuration du mock pour simuler un processus réussi pour rebalance_channel
        with patch.object(automation_manager, "rebalance_channel") as mock_rebalance:
            mock_rebalance.return_value = {
                "success": True,
                "message": "Rééquilibrage réussi pour le canal test_channel",
                "details": "Rebalance successful"
            }
            
            # Appel de la méthode
            result = await automation_manager.custom_rebalance_strategy("test_channel", 0.5)
            
            # Vérifications
            assert result["success"] is True
            assert "Rééquilibrage réussi" in result["message"]
            assert mock_rebalance.called
            assert mock_rebalance.call_args[0][0] == "test_channel"
            assert mock_rebalance.call_args[0][1] == 3000000  # 8000000 - (10000000 * 0.5)
            assert mock_rebalance.call_args[0][2] == "outgoing"

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_no_action_needed(automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée quand aucune action n'est nécessaire"""
    # Configuration du mock pour simuler un processus réussi pour getchaninfo
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour 0 (succès) pour getchaninfo
        mock_process = MagicMock()
        mock_process.returncode = 0
        channel_info = {
            "capacity": 10000000,
            "local_balance": 5100000  # Proche de 50%
        }
        mock_process.communicate = AsyncMock(return_value=(json.dumps(channel_info).encode(), b""))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.custom_rebalance_strategy("test_channel", 0.5)
        
        # Vérifications
        assert result["success"] is True
        assert "Déséquilibre faible" in result["message"]
        assert result["details"]["current_ratio"] == 0.51
        assert result["details"]["target_ratio"] == 0.5
        assert result["details"]["amount"] == 100000

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_getchaninfo_failure(automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée avec échec de getchaninfo"""
    # Configuration du mock pour simuler un processus échoué pour getchaninfo
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Configuration du mock pour retourner un code de retour non nul (échec) pour getchaninfo
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: Channel not found"))
        mock_exec.return_value = mock_process
        
        # Appel de la méthode
        result = await automation_manager.custom_rebalance_strategy("invalid_channel", 0.5)
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors de la récupération des informations du canal" in result["message"]

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_lnbits_success(lnbits_automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée via LNbits avec succès"""
    # Configuration du mock pour simuler une requête HTTP réussie pour getchaninfo
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Configuration du mock pour retourner un statut 200 (succès) pour getchaninfo
        mock_response = MagicMock()
        mock_response.status = 200
        channel_info = {
            "capacity": 10000000,
            "local_balance": 8000000
        }
        mock_response.json = AsyncMock(return_value=channel_info)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Configuration du mock pour simuler une requête HTTP réussie pour rebalance_channel
        with patch("aiohttp.ClientSession.post") as mock_post:
            # Configuration du mock pour retourner un statut 200 (succès) pour rebalance_channel
            mock_rebalance_response = MagicMock()
            mock_rebalance_response.status = 200
            mock_rebalance_response.json = AsyncMock(return_value={"status": "success", "txid": "123456"})
            mock_post.return_value.__aenter__.return_value = mock_rebalance_response
            
            # Appel de la méthode
            result = await lnbits_automation_manager.custom_rebalance_strategy("test_channel", 0.5)
            
            # Vérifications
            assert result["success"] is True
            assert "Rééquilibrage réussi" in result["message"]
            
            # Vérification de l'appel à l'API pour getchaninfo
            mock_get.assert_called_once()
            get_call_args = mock_get.call_args[1]
            assert "headers" in get_call_args
            assert get_call_args["headers"]["X-Api-Key"] == "test_api_key"
            
            # Vérification de l'appel à l'API pour rebalance_channel
            mock_post.assert_called_once()
            post_call_args = mock_post.call_args[1]
            assert "headers" in post_call_args
            assert post_call_args["headers"]["X-Api-Key"] == "test_api_key"
            assert "json" in post_call_args
            assert post_call_args["json"]["amount"] == 3000000  # 8000000 - (10000000 * 0.5)
            assert post_call_args["json"]["direction"] == "outgoing"

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_lnbits_no_action_needed(lnbits_automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée via LNbits quand aucune action n'est nécessaire"""
    # Configuration du mock pour simuler une requête HTTP réussie pour getchaninfo
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Configuration du mock pour retourner un statut 200 (succès) pour getchaninfo
        mock_response = MagicMock()
        mock_response.status = 200
        channel_info = {
            "capacity": 10000000,
            "local_balance": 5100000  # Proche de 50%
        }
        mock_response.json = AsyncMock(return_value=channel_info)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.custom_rebalance_strategy("test_channel", 0.5)
        
        # Vérifications
        assert result["success"] is True
        assert "Déséquilibre faible" in result["message"]
        assert result["details"]["current_ratio"] == 0.51
        assert result["details"]["target_ratio"] == 0.5
        assert result["details"]["amount"] == 100000

@pytest.mark.asyncio
async def test_custom_rebalance_strategy_lnbits_getchaninfo_failure(lnbits_automation_manager):
    """Test de la stratégie de rééquilibrage personnalisée via LNbits avec échec de getchaninfo"""
    # Configuration du mock pour simuler une requête HTTP échouée pour getchaninfo
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Configuration du mock pour retourner un statut 400 (échec) pour getchaninfo
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"detail": "Channel not found"})
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Appel de la méthode
        result = await lnbits_automation_manager.custom_rebalance_strategy("invalid_channel", 0.5)
        
        # Vérifications
        assert result["success"] is False
        assert "Erreur lors de la récupération des informations du canal via LNbits" in result["message"]

def test_get_automation_history(automation_manager):
    """Test de la récupération de l'historique des automatisations"""
    # Ajout d'entrées d'historique
    automation_manager.automation_history = [
        {
            "type": "fee_update",
            "channel_id": "channel1",
            "base_fee": 1000,
            "fee_rate": 0.0001,
            "timestamp": "2023-01-01T12:00:00",
            "success": True,
            "backend": "lncli"
        },
        {
            "type": "rebalance",
            "channel_id": "channel2",
            "amount": 1000000,
            "direction": "outgoing",
            "timestamp": "2023-01-02T12:00:00",
            "success": True,
            "backend": "rebalance-lnd"
        },
        {
            "type": "fee_update",
            "channel_id": "channel3",
            "base_fee": 2000,
            "fee_rate": 0.0002,
            "timestamp": "2023-01-03T12:00:00",
            "success": False,
            "backend": "lncli"
        }
    ]
    
    # Test avec limite par défaut
    history = automation_manager.get_automation_history()
    assert len(history) == 3
    assert history[0]["channel_id"] == "channel3"  # Le plus récent en premier
    
    # Test avec limite personnalisée
    history = automation_manager.get_automation_history(limit=2)
    assert len(history) == 2
    assert history[0]["channel_id"] == "channel3"
    assert history[1]["channel_id"] == "channel2" 