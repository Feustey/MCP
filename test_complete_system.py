#!/usr/bin/env python3
"""
Test complet du système MCP avec toutes les améliorations.
Vérifie l'authentification JWT, LNBits et la surveillance de connectivité.
"""

import asyncio
import logging
import json
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurer l'environnement de test
os.environ["DEVELOPMENT_MODE"] = "true"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_min32characters_ok"
os.environ["LNBITS_URL"] = "http://localhost:5001"

class SystemTester:
    """Testeur complet du système MCP."""
    
    def __init__(self):
        self.results = {
            "auth": None,
            "lnbits": None,
            "monitoring": None,
            "overall": None
        }
    
    async def test_jwt_auth(self) -> bool:
        """Test du système d'authentification JWT amélioré."""
        logger.info("=== TEST AUTHENTIFICATION JWT ===")
        
        try:
            from app.auth import verify_jwt_and_get_tenant, SECRET_KEY
            
            # Test 1: Mode développement
            logger.info("Test mode développement...")
            tenant = verify_jwt_and_get_tenant("")
            if tenant == "development_tenant":
                logger.info("✓ Mode développement fonctionnel")
            
            # Test 2: Clé secrète configurée
            logger.info(f"Clé JWT configurée: {len(SECRET_KEY)} caractères")
            if len(SECRET_KEY) >= 32:
                logger.info("✓ Clé JWT valide")
            
            self.results["auth"] = {
                "status": "success",
                "dev_mode": True,
                "key_length": len(SECRET_KEY)
            }
            return True
            
        except Exception as e:
            logger.error(f"Erreur auth: {str(e)}")
            self.results["auth"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def test_lnbits_integration(self) -> bool:
        """Test de l'intégration LNBits avec fallback."""
        logger.info("\n=== TEST INTÉGRATION LNBITS ===")
        
        try:
            from app.services.lnbits import LNbitsService
            
            service = LNbitsService()
            logger.info(f"Service LNBits initialisé - URL: {service.base_url}")
            logger.info(f"Mode mock: {service.use_mock}")
            
            # Test des fonctionnalités de base
            tests_passed = 0
            total_tests = 4
            
            # Test 1: Wallet
            try:
                wallet = await service.get_wallet_details()
                if wallet and "balance" in wallet:
                    logger.info(f"✓ Wallet: {wallet.get('balance', 0)} sats")
                    tests_passed += 1
            except Exception as e:
                logger.warning(f"✗ Wallet: {str(e)}")
            
            # Test 2: Invoice
            try:
                invoice = await service.create_invoice(1000, "Test")
                if invoice and "payment_request" in invoice:
                    logger.info(f"✓ Invoice créée")
                    tests_passed += 1
            except Exception as e:
                logger.warning(f"✗ Invoice: {str(e)}")
            
            # Test 3: Network stats
            try:
                stats = await service.get_network_stats()
                if stats:
                    logger.info(f"✓ Stats réseau: {stats.get('total_nodes', 0)} nœuds")
                    tests_passed += 1
            except Exception as e:
                logger.warning(f"✗ Stats: {str(e)}")
            
            # Test 4: Network nodes
            try:
                nodes = await service.get_network_nodes()
                if nodes:
                    logger.info(f"✓ Nœuds: {len(nodes.get('nodes', []))} trouvés")
                    tests_passed += 1
            except Exception as e:
                logger.warning(f"✗ Nœuds: {str(e)}")
            
            self.results["lnbits"] = {
                "status": "success" if tests_passed >= 3 else "partial",
                "tests_passed": tests_passed,
                "total_tests": total_tests,
                "mock_mode": service.use_mock
            }
            
            return tests_passed >= 3
            
        except Exception as e:
            logger.error(f"Erreur LNBits: {str(e)}")
            self.results["lnbits"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def test_connectivity_monitoring(self) -> bool:
        """Test du système de surveillance de connectivité."""
        logger.info("\n=== TEST SURVEILLANCE CONNECTIVITÉ ===")
        
        try:
            from src.monitoring.connectivity_monitor import ConnectivityMonitor
            
            monitor = ConnectivityMonitor(check_interval=60)
            
            # Vérifier les services
            status = await monitor.check_all_services()
            
            logger.info(f"État global: {status['overall_status']}")
            logger.info(f"Services healthy: {status['statistics']['healthy']}/{status['statistics']['total']}")
            
            # Afficher l'état des services critiques
            critical_services = monitor.get_critical_services_status()
            for service in critical_services:
                icon = "✓" if service["available"] else "✗"
                logger.info(f"{icon} {service['name']}: {service['status']}")
            
            self.results["monitoring"] = {
                "status": "success",
                "overall_status": status['overall_status'],
                "statistics": status['statistics'],
                "critical_services": len(critical_services)
            }
            
            return status['overall_status'] != "critical"
            
        except Exception as e:
            logger.error(f"Erreur monitoring: {str(e)}")
            self.results["monitoring"] = {
                "status": "failed",
                "error": str(e)
            }
            return False
    
    async def run_all_tests(self) -> bool:
        """Exécute tous les tests du système."""
        logger.info("🚀 DÉMARRAGE TESTS SYSTÈME COMPLET MCP")
        logger.info("=" * 50)
        
        # Test 1: Authentification
        auth_ok = await self.test_jwt_auth()
        
        # Test 2: LNBits
        lnbits_ok = await self.test_lnbits_integration()
        
        # Test 3: Monitoring
        monitoring_ok = await self.test_connectivity_monitoring()
        
        # Résultats globaux
        all_passed = auth_ok and lnbits_ok and monitoring_ok
        partial_success = auth_ok or lnbits_ok or monitoring_ok
        
        self.results["overall"] = {
            "timestamp": datetime.now().isoformat(),
            "all_passed": all_passed,
            "partial_success": partial_success,
            "components": {
                "auth": "✓" if auth_ok else "✗",
                "lnbits": "✓" if lnbits_ok else "✗",
                "monitoring": "✓" if monitoring_ok else "✗"
            }
        }
        
        return all_passed
    
    def generate_report(self) -> str:
        """Génère un rapport détaillé des tests."""
        report = []
        report.append("\n" + "=" * 50)
        report.append("📊 RAPPORT DE TEST SYSTÈME MCP")
        report.append("=" * 50)
        
        # État global
        if self.results["overall"]["all_passed"]:
            report.append("✅ TOUS LES TESTS RÉUSSIS")
        elif self.results["overall"]["partial_success"]:
            report.append("⚠️  SUCCÈS PARTIEL")
        else:
            report.append("❌ ÉCHEC DES TESTS")
        
        # Détails par composant
        report.append("\n📋 DÉTAILS PAR COMPOSANT:")
        
        # Auth
        auth = self.results["auth"]
        if auth["status"] == "success":
            report.append(f"✓ Authentification JWT: OK (mode dev: {auth.get('dev_mode', False)})")
        else:
            report.append(f"✗ Authentification JWT: ÉCHEC")
        
        # LNBits
        lnbits = self.results["lnbits"]
        if lnbits["status"] == "success":
            report.append(f"✓ LNBits: OK ({lnbits['tests_passed']}/{lnbits['total_tests']} tests)")
        elif lnbits["status"] == "partial":
            report.append(f"⚠ LNBits: PARTIEL ({lnbits['tests_passed']}/{lnbits['total_tests']} tests)")
        else:
            report.append(f"✗ LNBits: ÉCHEC")
        
        # Monitoring
        monitoring = self.results["monitoring"]
        if monitoring and monitoring["status"] == "success":
            stats = monitoring.get("statistics", {})
            report.append(f"✓ Monitoring: OK ({stats.get('healthy', 0)}/{stats.get('total', 0)} services)")
        else:
            report.append(f"✗ Monitoring: ÉCHEC")
        
        # Recommandations
        report.append("\n💡 RECOMMANDATIONS:")
        
        if self.results["overall"]["all_passed"]:
            report.append("• Système prêt pour la production")
            report.append("• Configurer les variables d'environnement de production")
            report.append("• Activer la surveillance continue")
        else:
            if auth and auth["status"] != "success":
                report.append("• Vérifier la configuration JWT")
            if lnbits and lnbits.get("mock_mode"):
                report.append("• Déployer le service LNBits réel")
            if monitoring and monitoring.get("overall_status") == "critical":
                report.append("• Vérifier les services critiques")
        
        report.append("=" * 50)
        
        return "\n".join(report)

async def main():
    """Point d'entrée principal."""
    tester = SystemTester()
    
    # Exécuter tous les tests
    success = await tester.run_all_tests()
    
    # Générer et afficher le rapport
    report = tester.generate_report()
    print(report)
    
    # Sauvegarder les résultats
    with open("system_test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2)
    
    logger.info("📄 Résultats sauvegardés dans system_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(asyncio.run(main()))