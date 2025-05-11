#!/usr/bin/env python3
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import tempfile

from liquidity_scanner import LiquidityScanManager


@pytest.fixture
def lnbits_client_mock():
    """Fixture pour créer un mock du client LNBits."""
    client = AsyncMock()
    
    # Simuler des canaux de test
    test_channels = [
        {
            "channel_id": "channel1",
            "capacity": 3_000_000,
            "remote_pubkey": "peer1",
            "remote_balance": 600_000
        },
        {
            "channel_id": "channel2",
            "capacity": 4_000_000,
            "remote_pubkey": "peer2",
            "remote_balance": 200_000
        },
        {
            "channel_id": "channel3",
            "capacity": 5_000_000,
            "remote_pubkey": "peer3",
            "remote_balance": 700_000
        }
    ]
    
    # Multiplier les canaux pour atteindre le seuil d'éligibilité
    expanded_channels = []
    for i in range(20):  # 20 canaux, plus que le minimum requis
        for channel in test_channels:
            new_channel = channel.copy()
            new_channel["channel_id"] = f"{channel['channel_id']}_{i}"
            new_channel["remote_pubkey"] = f"{channel['remote_pubkey']}_{i}"
            expanded_channels.append(new_channel)
    
    client.get_node_channels.return_value = expanded_channels
    
    # Simuler les paiements de test - corriger le mock
    client.send_test_payment.return_value = {"success": True, "fee_paid": 10}
    
    return client


@pytest.fixture
def scanner(lnbits_client_mock):
    """Fixture pour créer une instance du LiquidityScanManager."""
    scanner = LiquidityScanManager(lnbits_client=lnbits_client_mock)
    # Patcher la méthode de sauvegarde
    scanner.data_dir = MagicMock()
    return scanner


@pytest.mark.asyncio
async def test_node_eligibility(scanner, lnbits_client_mock):
    """Teste la vérification d'éligibilité d'un nœud."""
    # Test avec un nœud éligible
    result = await scanner.is_node_eligible("test_node")
    assert result is True
    
    # Test avec un nœud non éligible (pas assez de canaux)
    lnbits_client_mock.get_node_channels.return_value = [
        {"channel_id": "ch1", "capacity": 3_000_000, "remote_pubkey": "peer1", "remote_balance": 600_000}
    ]
    result = await scanner.is_node_eligible("small_node")
    assert result is False


@pytest.mark.asyncio
async def test_scan_channel_liquidity(scanner):
    """Teste le scan de liquidité d'un canal spécifique."""
    result = await scanner.scan_channel_liquidity("channel1", "source_node", "target_node")
    
    assert result["channel_id"] == "channel1"
    assert result["source"] == "source_node"
    assert result["target"] == "target_node"
    assert result["outbound_success"] is True
    assert result["inbound_success"] is True


@pytest.mark.asyncio
async def test_bulk_scan_node_channels(scanner, lnbits_client_mock):
    """Teste le scan en masse des canaux d'un nœud."""
    result = await scanner.bulk_scan_node_channels("test_node", sample_size=3)
    
    assert result["eligible"] is True
    assert result["node_pubkey"] == "test_node"
    assert "tested_channels" in result
    assert "bidirectional_count" in result
    assert "liquidity_score" in result
    
    # Vérifier qu'il y a bien 3 canaux testés
    assert len(result["results"]) == 3


@pytest.mark.asyncio
async def test_calculate_liquidity_score(scanner):
    """Teste le calcul du score de liquidité."""
    # Créer des données de test
    scan_data = {
        "results": [{}, {}, {}, {}],  # 4 canaux
        "bidirectional_count": 2,      # 2 canaux bidirectionnels
        "outbound_only_count": 1,      # 1 canal sortant uniquement
        "inbound_only_count": 1        # 1 canal entrant uniquement
    }
    
    score = scanner.calculate_liquidity_score(scan_data)
    
    # Score attendu: (2/4*100)*0.7 + (1/4*100)*0.15 + (1/4*100)*0.15 = 42.5
    assert score == 42.5


@pytest.mark.asyncio
async def test_save_scan_results(scanner):
    """Teste la sauvegarde des résultats de scan."""
    # Simuler des résultats de scan
    scanner.scan_results = {
        "channel1": {"channel_id": "channel1", "outbound_success": True, "inbound_success": False, "source": "node1", "target": "remote1"}
    }
    
    # Créer un chemin de test réel pour éviter les problèmes de mocking
    temp_dir = tempfile.mkdtemp()
    test_path = Path(temp_dir)
    scanner.data_dir = test_path
    
    # Utiliser un timestamp fixe pour la cohérence des tests
    fixed_timestamp = "20250401_120000"
    expected_file = test_path / f"liquidity_scan_results_{fixed_timestamp}.json"
    expected_link = test_path / "latest_liquidity_scan.json"
    
    try:
        # Patcher datetime pour avoir un timestamp consistant
        with patch('liquidity_scanner.datetime') as mock_datetime, \
             patch('pathlib.Path.symlink_to') as mock_symlink:
            # Configurer le mock de datetime
            mock_dt_instance = MagicMock()
            mock_dt_instance.isoformat.return_value = "2025-04-01T12:00:00"
            mock_dt_instance.strftime.return_value = fixed_timestamp
            mock_datetime.now.return_value = mock_dt_instance
            mock_datetime.strftime = datetime.strftime
            
            # Exécuter la méthode testée
            result_path = await scanner.save_scan_results({"node1": "Test Node"})
        
            # Vérifier que le fichier a été créé
            assert Path(result_path).exists()
            
            # Vérifier le contenu du fichier
            with open(result_path, 'r') as f:
                data = json.load(f)
                assert "node_results" in data
                assert "Test Node" == data["node_results"]["node1"]["alias"]
                assert "scan_date" in data
    finally:
        # Nettoyage des fichiers de test
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main(["-xvs", "test_liquidity_scanner.py"]) 