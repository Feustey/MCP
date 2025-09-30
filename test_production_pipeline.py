#!/usr/bin/env python3
"""
Test end-to-end du pipeline MCP en mode production (shadow mode)

Ce script teste:
1. Connexion à l'API MCP
2. Vérification des endpoints health
3. Test du Core Fee Optimizer en dry-run
4. Validation du système de rollback
5. Métriques de performance

Dernière mise à jour: 30 septembre 2025
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json

# Configuration
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Charge les variables d'environnement
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# Imports locaux
try:
    from src.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class ProductionPipelineTest:
    """Test du pipeline complet en conditions de production"""

    def __init__(self):
        self.results = {
            "tests": [],
            "total": 0,
            "passed": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat()
        }
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    def log_test(self, name: str, passed: bool, message: str = "", duration: float = 0):
        """Log un résultat de test"""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {name} ({duration:.2f}s)")
        if message:
            logger.info(f"    {message}")

        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "message": message,
            "duration": duration
        })
        self.results["total"] += 1
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

    async def test_health_endpoints(self) -> bool:
        """Test des endpoints de santé"""
        import httpx

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test health endpoint
                response = await client.get(f"{self.api_base_url}/api/v1/health")
                assert response.status_code == 200, f"Status: {response.status_code}"
                data = response.json()
                assert data.get("status") == "healthy", "Status not healthy"

                self.log_test("Health Endpoint", True,
                            f"Status: {data.get('status')}", time.time() - start)
                return True

        except Exception as e:
            self.log_test("Health Endpoint", False, str(e), time.time() - start)
            return False

    async def test_core_fee_optimizer_dry_run(self) -> bool:
        """Test du Core Fee Optimizer en mode dry-run"""
        start = time.time()
        try:
            # Import et initialisation
            from src.optimizers.core_fee_optimizer import CoreFeeOptimizer

            # Utilise un pubkey de test ou feustey
            test_pubkey = os.getenv("TEST_NODE_PUBKEY",
                                   "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

            # Test sans connexion LND réelle (mock les credentials)
            optimizer = CoreFeeOptimizer(
                node_pubkey=test_pubkey,
                dry_run=True,  # Mode shadow
                max_changes_per_run=3,
                backup_enabled=True,
                lnd_host="localhost",
                lnd_port=8080,
                macaroon_path="/tmp/mock.macaroon",  # Fichier mock
                tls_cert_path="/tmp/mock.cert"  # Fichier mock
            )

            # Test de l'initialisation
            assert optimizer.dry_run == True, "Dry-run should be enabled"
            assert optimizer.backup_enabled == True, "Backup should be enabled"
            assert optimizer.node_pubkey == test_pubkey, "Pubkey mismatch"

            self.log_test("Core Fee Optimizer Init", True,
                        f"Optimizer initialized for node {test_pubkey[:8]} (mock mode)",
                        time.time() - start)
            return True

        except Exception as e:
            self.log_test("Core Fee Optimizer Init", False, str(e), time.time() - start)
            return False

    async def test_rollback_system(self) -> bool:
        """Test du système de rollback"""
        start = time.time()
        try:
            # Vérifie que le dossier de rollback existe
            rollback_dir = ROOT_DIR / "data" / "rollbacks"
            rollback_dir.mkdir(parents=True, exist_ok=True)

            # Crée un fichier de test
            test_backup = {
                "timestamp": datetime.now().isoformat(),
                "test": True,
                "channels": []
            }

            test_file = rollback_dir / f"test_backup_{int(time.time())}.json"
            with open(test_file, 'w') as f:
                json.dump(test_backup, f)

            # Vérifie la création
            assert test_file.exists(), "Backup file not created"

            # Nettoyage
            test_file.unlink()

            self.log_test("Rollback System", True,
                        f"Backup directory: {rollback_dir}",
                        time.time() - start)
            return True

        except Exception as e:
            self.log_test("Rollback System", False, str(e), time.time() - start)
            return False

    async def test_environment_config(self) -> bool:
        """Test de la configuration d'environnement"""
        start = time.time()
        try:
            required_vars = [
                "MONGO_URL",
                "JWT_SECRET",
                "ENVIRONMENT"
            ]

            missing = []
            for var in required_vars:
                if not os.getenv(var):
                    missing.append(var)

            if missing:
                self.log_test("Environment Config", False,
                            f"Missing vars: {', '.join(missing)}",
                            time.time() - start)
                return False

            env = os.getenv("ENVIRONMENT", "unknown")
            dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

            self.log_test("Environment Config", True,
                        f"ENV={env}, DRY_RUN={dry_run}",
                        time.time() - start)
            return True

        except Exception as e:
            self.log_test("Environment Config", False, str(e), time.time() - start)
            return False

    async def test_simulator_availability(self) -> bool:
        """Test de disponibilité du simulateur"""
        start = time.time()
        try:
            from src.tools.node_simulator import NODE_BEHAVIORS

            assert len(NODE_BEHAVIORS) >= 5, "Not enough node profiles"

            profiles = list(NODE_BEHAVIORS.keys())

            self.log_test("Simulator Availability", True,
                        f"Profiles: {', '.join(profiles)}",
                        time.time() - start)
            return True

        except Exception as e:
            self.log_test("Simulator Availability", False, str(e), time.time() - start)
            return False

    async def run_all_tests(self):
        """Exécute tous les tests"""
        logger.info("="*60)
        logger.info("🚀 PHASE 5 - Production Pipeline Test")
        logger.info(f"Timestamp: {self.results['start_time']}")
        logger.info(f"API Base URL: {self.api_base_url}")
        logger.info("="*60)

        # Tests synchrones
        await self.test_environment_config()
        await self.test_rollback_system()
        await self.test_simulator_availability()
        await self.test_core_fee_optimizer_dry_run()

        # Tests API (peuvent échouer si l'API n'est pas démarrée)
        logger.info("\n--- API Tests (optional) ---")
        await self.test_health_endpoints()

        # Résumé
        self.results["end_time"] = datetime.now().isoformat()

        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tests: {self.results['total']}")
        logger.info(f"Passed: {self.results['passed']} ✅")
        logger.info(f"Failed: {self.results['failed']} ❌")

        pass_rate = (self.results['passed'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        logger.info(f"Pass rate: {pass_rate:.1f}%")

        # Sauvegarde des résultats
        results_file = ROOT_DIR / "data" / "test_results" / f"pipeline_test_{int(time.time())}.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"\nResults saved to: {results_file}")
        logger.info("="*60)

        return self.results['failed'] == 0


async def main():
    """Point d'entrée principal"""
    test = ProductionPipelineTest()
    success = await test.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
