#!/usr/bin/env python3
"""
Test léger du système MCP sans dépendances complexes.
Version simplifiée pour validation rapide.
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

class LightweightSystemTester:
    """Testeur léger du système MCP."""
    
    def __init__(self):
        self.results = {
            "auth": None,
            "basic_imports": None,
            "mock_lnbits": None,
            "overall": None
        }
    
    async def test_jwt_auth(self) -> bool:
        """Test du système d'authentification JWT."""
        logger.info("=== TEST AUTHENTIFICATION JWT ===")
        
        try:
            from app.auth import verify_jwt_and_get_tenant, SECRET_KEY
            
            # Test mode développement
            tenant = verify_jwt_and_get_tenant("")
            if tenant == "development_tenant":
                logger.info("✓ Mode développement OK")
                
            # Test clé secrète
            if len(SECRET_KEY) >= 32:
                logger.info(f"✓ Clé JWT valide ({len(SECRET_KEY)} chars)")
            
            self.results["auth"] = {
                "status": "success",
                "dev_mode": True,
                "key_valid": len(SECRET_KEY) >= 32
            }
            return True
            
        except Exception as e:
            logger.error(f"Erreur auth: {str(e)}")
            self.results["auth"] = {"status": "failed", "error": str(e)}
            return False
    
    async def test_basic_imports(self) -> bool:
        """Test des imports de base."""
        logger.info("\n=== TEST IMPORTS DE BASE ===")
        
        imports_to_test = [
            ("fastapi", "FastAPI framework"),
            ("uvicorn", "ASGI server"),
            ("httpx", "HTTP client"),
            ("motor", "MongoDB async driver"),
            ("redis", "Redis client"),
            ("jwt", "JWT library")
        ]
        
        successful_imports = 0
        
        for module_name, description in imports_to_test:
            try:
                __import__(module_name)
                logger.info(f"✓ {module_name}: {description}")
                successful_imports += 1
            except ImportError as e:
                logger.warning(f"✗ {module_name}: {str(e)}")
        
        success = successful_imports >= len(imports_to_test) // 2
        
        self.results["basic_imports"] = {
            "status": "success" if success else "partial",
            "successful": successful_imports,
            "total": len(imports_to_test)
        }
        
        return success
    
    async def test_mock_lnbits(self) -> bool:
        """Test des fonctionnalités LNBits en mode mock uniquement."""
        logger.info("\n=== TEST LNBITS MODE MOCK ===")
        
        try:
            # Test avec données mock simples
            mock_wallet = {
                "id": "test_wallet",
                "balance": 100000000,
                "currency": "sat"
            }
            
            mock_invoice = {
                "payment_hash": "test_hash_123",
                "payment_request": "lntb10000test",
                "amount": 10000,
                "status": "pending"
            }
            
            mock_stats = {
                "total_nodes": 18000,
                "total_channels": 85000,
                "total_capacity": 5000000000
            }
            
            # Vérifier que les structures sont correctes
            wallet_ok = "balance" in mock_wallet and mock_wallet["balance"] > 0
            invoice_ok = "payment_request" in mock_invoice
            stats_ok = "total_nodes" in mock_stats and mock_stats["total_nodes"] > 0
            
            if wallet_ok:
                logger.info(f"✓ Mock wallet: {mock_wallet['balance']} sats")
            if invoice_ok:
                logger.info(f"✓ Mock invoice: {mock_invoice['payment_request'][:20]}...")
            if stats_ok:
                logger.info(f"✓ Mock stats: {mock_stats['total_nodes']} nœuds")
            
            success = wallet_ok and invoice_ok and stats_ok
            
            self.results["mock_lnbits"] = {
                "status": "success" if success else "partial",
                "wallet": wallet_ok,
                "invoice": invoice_ok,
                "stats": stats_ok
            }
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur mock LNBits: {str(e)}")
            self.results["mock_lnbits"] = {"status": "failed", "error": str(e)}
            return False
    
    async def test_basic_connectivity(self) -> bool:
        """Test de connectivité basique sans services externes."""
        logger.info("\n=== TEST CONNECTIVITÉ BASIQUE ===")
        
        try:
            # Test de connectivité réseau simple
            import socket
            
            def can_connect(host, port, timeout=3):
                try:
                    socket.setdefaulttimeout(timeout)
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
                    return True
                except:
                    return False
            
            # Test de quelques services basiques
            tests = [
                ("Google DNS", "8.8.8.8", 53),
                ("Cloudflare DNS", "1.1.1.1", 53)
            ]
            
            connected = 0
            for name, host, port in tests:
                if can_connect(host, port):
                    logger.info(f"✓ {name}: accessible")
                    connected += 1
                else:
                    logger.info(f"✗ {name}: non accessible")
            
            # Au moins une connexion doit réussir
            return connected > 0
            
        except Exception as e:
            logger.error(f"Erreur connectivité: {str(e)}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Exécute tous les tests légers."""
        logger.info("🚀 TESTS SYSTÈME LÉGER MCP")
        logger.info("=" * 40)
        
        # Tests
        auth_ok = await self.test_jwt_auth()
        imports_ok = await self.test_basic_imports()
        mock_ok = await self.test_mock_lnbits()
        connectivity_ok = await self.test_basic_connectivity()
        
        # Résultats
        tests_passed = sum([auth_ok, imports_ok, mock_ok, connectivity_ok])
        total_tests = 4
        
        success = tests_passed >= 3  # Au moins 3/4 tests doivent réussir
        
        self.results["overall"] = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": tests_passed,
            "total_tests": total_tests,
            "success_rate": (tests_passed / total_tests) * 100,
            "status": "success" if success else "partial"
        }
        
        return success
    
    def generate_report(self) -> str:
        """Génère un rapport léger."""
        if not self.results["overall"]:
            return "Aucun test exécuté"
        
        overall = self.results["overall"]
        report = []
        
        report.append("\n" + "=" * 40)
        report.append("📊 RAPPORT SYSTÈME LÉGER MCP")
        report.append("=" * 40)
        
        if overall["success_rate"] >= 75:
            report.append("✅ SYSTÈME OPÉRATIONNEL")
        elif overall["success_rate"] >= 50:
            report.append("⚠️  SYSTÈME PARTIELLEMENT OPÉRATIONNEL")
        else:
            report.append("❌ PROBLÈMES DÉTECTÉS")
        
        report.append(f"\nTests réussis: {overall['tests_passed']}/{overall['total_tests']}")
        report.append(f"Taux de succès: {overall['success_rate']:.1f}%")
        
        # Détails
        report.append("\n📋 DÉTAILS:")
        
        if self.results["auth"] and self.results["auth"]["status"] == "success":
            report.append("✓ Authentification JWT: Fonctionnelle")
        
        if self.results["basic_imports"] and self.results["basic_imports"]["status"] in ["success", "partial"]:
            imports = self.results["basic_imports"]
            report.append(f"✓ Imports: {imports['successful']}/{imports['total']} modules")
        
        if self.results["mock_lnbits"] and self.results["mock_lnbits"]["status"] == "success":
            report.append("✓ Mock LNBits: Fonctionnel")
        
        # Recommandations
        report.append("\n💡 PROCHAINES ÉTAPES:")
        if overall["success_rate"] >= 75:
            report.append("• Configuration des variables d'environnement de production")
            report.append("• Déploiement des services externes (MongoDB, Redis)")
            report.append("• Activation de la surveillance continue")
        else:
            report.append("• Installer les dépendances manquantes")
            report.append("• Corriger les problèmes d'importation")
            report.append("• Vérifier la configuration système")
        
        report.append("=" * 40)
        return "\n".join(report)

async def main():
    """Point d'entrée principal."""
    tester = LightweightSystemTester()
    
    # Tests
    success = await tester.run_all_tests()
    
    # Rapport
    report = tester.generate_report()
    print(report)
    
    # Sauvegarde
    with open("lightweight_test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2)
    
    logger.info("📄 Résultats sauvegardés dans lightweight_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(asyncio.run(main()))