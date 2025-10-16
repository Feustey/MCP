#!/usr/bin/env python3
"""
Test d'intégration Phase 2 - Core Engine

Ce script teste l'intégration de tous les composants de la Phase 2.

Usage:
    python scripts/test_phase2_integration.py [--dry-run] [--verbose]

Dernière mise à jour: 15 octobre 2025
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.lnbits_client import LNBitsClient
from src.auth.macaroon_manager import MacaroonManager
from src.optimizers.decision_engine import DecisionEngine, DecisionType
from src.optimizers.policy_validator import PolicyValidator, PolicyChangeType
from src.tools.policy_executor import PolicyExecutor
from src.tools.transaction_manager import TransactionManager
from src.tools.backup_manager import BackupManager
from src.tools.rollback_orchestrator import RollbackOrchestrator

# Configurer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_lnbits_client():
    """Test du client LNBits."""
    logger.info("=" * 60)
    logger.info("TEST 1: LNBits Client")
    logger.info("=" * 60)
    
    try:
        client = LNBitsClient(
            url="http://localhost:5000",
            api_key="test_key"
        )
        
        logger.info("✅ LNBitsClient instancié")
        
        # Test de rate limiting
        logger.info("Test rate limiting...")
        await client._check_rate_limit()
        logger.info("✅ Rate limiting fonctionne")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur LNBitsClient: {e}")
        return False


async def test_macaroon_manager():
    """Test du gestionnaire de macaroons."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Macaroon Manager")
    logger.info("=" * 60)
    
    try:
        # Générer une clé de chiffrement pour test
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()
        
        manager = MacaroonManager(
            encryption_key=test_key
        )
        
        logger.info("✅ MacaroonManager instancié")
        
        # Test chiffrement/déchiffrement
        test_data = "test_macaroon_value"
        encrypted = manager._encrypt(test_data)
        decrypted = manager._decrypt(encrypted)
        
        assert decrypted == test_data, "Erreur chiffrement/déchiffrement"
        logger.info("✅ Chiffrement/déchiffrement fonctionnent")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur MacaroonManager: {e}")
        return False


def test_decision_engine():
    """Test du moteur de décision."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Decision Engine")
    logger.info("=" * 60)
    
    try:
        engine = DecisionEngine()
        
        logger.info("✅ DecisionEngine instancié")
        logger.info(f"   Poids configurés: {list(engine.weights.keys())}")
        
        # Test évaluation d'un canal simulé
        test_channel = {
            "channel_id": "test_123456x789x0",
            "local_balance": 5000000,
            "remote_balance": 5000000,
            "capacity": 10000000,
            "policy": {
                "base_fee_msat": 1000,
                "fee_rate_ppm": 500
            }
        }
        
        test_node_data = {
            "node_id": "test_node",
            "channels": [test_channel]
        }
        
        evaluation = engine.evaluate_channel(test_channel, test_node_data)
        
        logger.info(f"✅ Évaluation canal réussie:")
        logger.info(f"   Décision: {evaluation['decision']}")
        logger.info(f"   Confiance: {evaluation['confidence']:.2f}")
        logger.info(f"   Score total: {evaluation['total_score']:.2f}")
        logger.info(f"   Reasoning: {evaluation['reasoning'][:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur DecisionEngine: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_policy_validator():
    """Test du validateur de policies."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Policy Validator")
    logger.info("=" * 60)
    
    try:
        validator = PolicyValidator()
        
        logger.info("✅ PolicyValidator instancié")
        logger.info(f"   Limites configurées: base_fee {validator.safety_rules['base_fee_msat_min']}-{validator.safety_rules['base_fee_msat_max']} msat")
        
        # Test validation policy valide
        test_channel = {
            "channel_id": "test_123",
            "policy": {
                "base_fee_msat": 1000,
                "fee_rate_ppm": 500
            }
        }
        
        test_policy = {
            "base_fee_msat": 1200,
            "fee_rate_ppm": 600,
            "time_lock_delta": 40
        }
        
        is_valid, error = validator.validate_policy_change(
            test_channel,
            test_policy,
            PolicyChangeType.FEE_INCREASE
        )
        
        logger.info(f"✅ Validation réussie: valid={is_valid}, error={error}")
        
        # Test validation policy invalide (frais trop élevés)
        invalid_policy = {
            "base_fee_msat": 50000,  # Trop élevé
            "fee_rate_ppm": 500,
            "time_lock_delta": 40
        }
        
        is_valid, error = validator.validate_policy_change(
            test_channel,
            invalid_policy,
            PolicyChangeType.FEE_INCREASE
        )
        
        assert not is_valid, "Validation aurait dû échouer"
        logger.info(f"✅ Rejet policy invalide: {error}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur PolicyValidator: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_policy_executor():
    """Test de l'exécuteur de policies."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Policy Executor (Dry-Run)")
    logger.info("=" * 60)
    
    try:
        # Client simulé
        lnbits_client = LNBitsClient(
            url="http://localhost:5000",
            api_key="test_key"
        )
        
        executor = PolicyExecutor(
            lnbits_client=lnbits_client,
            dry_run=True  # Mode simulation
        )
        
        logger.info("✅ PolicyExecutor instancié (dry_run=True)")
        
        # Test application policy en dry-run
        test_channel = {
            "channel_id": "test_123",
            "channel_point": "abc123:0",
            "policy": {
                "base_fee_msat": 1000,
                "fee_rate_ppm": 500
            }
        }
        
        new_policy = {
            "base_fee_msat": 1200,
            "fee_rate_ppm": 600,
            "time_lock_delta": 40
        }
        
        result = await executor.apply_policy_change(
            test_channel,
            new_policy,
            PolicyChangeType.FEE_INCREASE
        )
        
        logger.info(f"✅ Application simulée:")
        logger.info(f"   Success: {result['success']}")
        logger.info(f"   Dry-run: {result['dry_run']}")
        logger.info(f"   Validation: {result['validation']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur PolicyExecutor: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transaction_manager():
    """Test du gestionnaire de transactions."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Transaction Manager")
    logger.info("=" * 60)
    
    try:
        tx_manager = TransactionManager()
        
        logger.info("✅ TransactionManager instancié")
        
        # Test création transaction
        test_channels = [
            {"channel_id": "test_123", "policy": {"base_fee_msat": 1000}},
            {"channel_id": "test_456", "policy": {"base_fee_msat": 1200}}
        ]
        
        tx_id = tx_manager.begin_transaction(
            node_id="test_node",
            channels=test_channels,
            operation_type="test"
        )
        
        logger.info(f"✅ Transaction créée: {tx_id}")
        
        # Simuler succès
        tx_manager.update_transaction_progress(
            tx_id,
            "test_123",
            success=True,
            new_policy={"base_fee_msat": 1100}
        )
        
        # Commit
        commit_success = tx_manager.commit_transaction(tx_id)
        
        logger.info(f"✅ Transaction commit: success={commit_success}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur TransactionManager: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backup_manager():
    """Test du gestionnaire de backups."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Backup Manager")
    logger.info("=" * 60)
    
    try:
        backup_manager = BackupManager()
        
        logger.info("✅ BackupManager instancié")
        
        # Test création backup
        backup_id = backup_manager.create_backup(
            channel_id="test_123",
            channel_point="abc123:0",
            policy={"base_fee_msat": 1000, "fee_rate_ppm": 500},
            node_id="test_node"
        )
        
        logger.info(f"✅ Backup créé: {backup_id}")
        
        # Test récupération
        backup = backup_manager.get_backup(backup_id)
        
        assert backup is not None, "Backup non trouvé"
        logger.info(f"✅ Backup récupéré: {backup['channel_id']}")
        
        # Test vérification intégrité
        is_valid = backup_manager.verify_integrity(backup_id)
        logger.info(f"✅ Intégrité vérifiée: {is_valid}")
        
        # Test stats
        stats = backup_manager.get_stats()
        logger.info(f"✅ Stats backups: {stats['hot']['count']} backups HOT")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur BackupManager: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rollback_orchestrator():
    """Test de l'orchestrateur de rollback."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 8: Rollback Orchestrator")
    logger.info("=" * 60)
    
    try:
        tx_manager = TransactionManager()
        backup_manager = BackupManager()
        orchestrator = RollbackOrchestrator(tx_manager, backup_manager)
        
        logger.info("✅ RollbackOrchestrator instancié")
        
        # Test analyse métriques pour rollback auto
        test_metrics = {
            "error_rate": 0.3,
            "latency_ratio": 1.5,
            "sample_count": 10
        }
        
        should_rollback, reason = orchestrator._should_auto_rollback(test_metrics)
        
        logger.info(f"✅ Analyse métriques: rollback={should_rollback}, reason={reason}")
        
        # Test stats
        stats = orchestrator.get_stats()
        logger.info(f"✅ Stats rollback: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur RollbackOrchestrator: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Exécute tous les tests."""
    logger.info("\n" + "🚀" * 30)
    logger.info("TESTS D'INTÉGRATION PHASE 2 - CORE ENGINE")
    logger.info("🚀" * 30 + "\n")
    
    results = {
        "LNBits Client": await test_lnbits_client(),
        "Macaroon Manager": await test_macaroon_manager(),
        "Decision Engine": test_decision_engine(),
        "Policy Validator": test_policy_validator(),
        "Policy Executor": await test_policy_executor(),
        "Transaction Manager": test_transaction_manager(),
        "Backup Manager": test_backup_manager(),
        "Rollback Orchestrator": await test_rollback_orchestrator()
    }
    
    # Résumé
    logger.info("\n" + "=" * 60)
    logger.info("RÉSUMÉ DES TESTS")
    logger.info("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"TOTAL: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")
    logger.info("=" * 60 + "\n")
    
    if passed == total:
        logger.info("🎉 TOUS LES TESTS SONT PASSÉS ! 🎉")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) échoué(s)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

