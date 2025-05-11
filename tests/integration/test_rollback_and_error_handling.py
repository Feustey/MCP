import pytest
import asyncio
from src.optimizers.core_fee_optimizer import CoreFeeOptimizer, OptimizationError
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_rollback_on_error(monkeypatch, tmp_path):
    """
    Simule une erreur lors de l'application d'une optimisation et vérifie que le rollback est déclenché.
    """
    # Préparer un optimizer avec dry_run désactivé pour simuler une vraie action
    optimizer = CoreFeeOptimizer(
        node_pubkey="testpubkey",
        dry_run=False,
        max_changes_per_run=2,
        backup_enabled=True
    )
    # Mocker LNDClient pour simuler une erreur lors de l'application
    optimizer.lnd_client = AsyncMock()
    optimizer.lnd_client.get_node_info.return_value = {"alias": "testnode"}
    optimizer.lnd_client.get_channels.return_value = [{"channel_id": "chan1"}]
    optimizer.lnd_client.get_node_metrics.return_value = {}
    optimizer.lnd_client.get_channel_policy.return_value = {"node1_policy": {"base_fee_msat": 1000, "fee_rate_ppm": 1}}
    optimizer.lnd_client.get_channel_info.return_value = {"node1_pubkey": "testpubkey", "node2_pubkey": "otherpubkey"}
    # Simuler une erreur lors de update_channel_fees
    with patch("src.optimizers.fee_update_utils.update_channel_fees", new=AsyncMock(side_effect=Exception("Erreur LND"))):
        # Exécuter le pipeline et vérifier que le rollback est tenté
        result = await optimizer.run_pipeline()
        assert result["status"] == "error"
        assert any("rollback" in err.get("rollback_result", {}) for err in result["errors"]), "Le rollback doit être tenté en cas d'erreur."

@pytest.mark.asyncio
async def test_offline_node(monkeypatch):
    """
    Simule un nœud offline et vérifie que l'erreur est logguée sans crash.
    """
    optimizer = CoreFeeOptimizer(
        node_pubkey="offlinepubkey",
        dry_run=True,
        max_changes_per_run=1,
        backup_enabled=True
    )
    # Mocker LNDClient pour simuler un nœud offline
    optimizer.lnd_client = AsyncMock()
    optimizer.lnd_client.get_node_info.side_effect = Exception("Nœud offline")
    with pytest.raises(Exception):
        await optimizer.run_pipeline()

@pytest.mark.asyncio
async def test_corrupted_backup(tmp_path):
    """
    Simule un fichier de backup corrompu et vérifie que le rollback échoue proprement.
    """
    optimizer = CoreFeeOptimizer(
        node_pubkey="corruptpubkey",
        dry_run=True,
        max_changes_per_run=1,
        backup_enabled=True
    )
    # Créer un backup corrompu
    backup_file = tmp_path / "backup_corrupt.json"
    with open(backup_file, "w") as f:
        f.write("{corrupted json}")
    optimizer.run_id = "corrupt_test"
    optimizer.original_state = {"chan1": {"channel_point": "point1", "policy": {}}}
    optimizer.applied_changes = [{"channel_id": "chan1", "channel_point": "point1"}]
    # Patch le chemin du backup
    with patch("src.optimizers.core_fee_optimizer.BACKUP_DIR", tmp_path):
        with pytest.raises(Exception):
            await optimizer._perform_rollback() 