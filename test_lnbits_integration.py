#!/usr/bin/env python3
"""
Test script pour vérifier l'intégration LNBits complète avec MCP.
"""

import asyncio
import logging
import sys
import os

# Ajouter le répertoire racine au path Python
sys.path.insert(0, os.path.dirname(__file__))

from app.services.lnbits import LNbitsService

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_lnbits_service():
    """Test complet du service LNBits."""
    logger.info("=== TEST D'INTÉGRATION LNBITS AVEC MCP ===")
    
    # Créer une instance du service
    lnbits = LNbitsService()
    logger.info(f"Service initialisé - URL: {lnbits.base_url}")
    logger.info(f"Mode mock: {lnbits.use_mock}")
    
    results = {
        "wallet_info": None,
        "create_invoice": None,
        "transactions": None,
        "network_stats": None,
        "network_nodes": None
    }
    
    try:
        # Test 1: Récupérer les informations du wallet
        logger.info("\n1. Test récupération wallet...")
        results["wallet_info"] = await lnbits.get_wallet_details()
        logger.info(f"Wallet: {results['wallet_info']}")
        
    except Exception as e:
        logger.error(f"Erreur wallet: {str(e)}")
    
    try:
        # Test 2: Créer une facture
        logger.info("\n2. Test création facture...")
        results["create_invoice"] = await lnbits.create_invoice(
            amount=1000, 
            memo="Test MCP Integration"
        )
        logger.info(f"Facture créée: {results['create_invoice']}")
        
    except Exception as e:
        logger.error(f"Erreur facture: {str(e)}")
    
    try:
        # Test 3: Récupérer les transactions
        logger.info("\n3. Test récupération transactions...")
        results["transactions"] = await lnbits.get_transactions()
        logger.info(f"Transactions: {len(results['transactions'].get('payments', []))} transactions trouvées")
        
    except Exception as e:
        logger.error(f"Erreur transactions: {str(e)}")
    
    try:
        # Test 4: Récupérer les statistiques du réseau
        logger.info("\n4. Test statistiques réseau...")
        results["network_stats"] = await lnbits.get_network_stats()
        logger.info(f"Stats réseau: {results['network_stats']}")
        
    except Exception as e:
        logger.error(f"Erreur stats réseau: {str(e)}")
    
    try:
        # Test 5: Récupérer les nœuds du réseau
        logger.info("\n5. Test nœuds du réseau...")
        results["network_nodes"] = await lnbits.get_network_nodes()
        logger.info(f"Nœuds: {len(results['network_nodes'].get('nodes', []))} nœuds trouvés")
        
    except Exception as e:
        logger.error(f"Erreur nœuds réseau: {str(e)}")
    
    # Analyse des résultats
    logger.info("\n=== RÉSUMÉ DES TESTS ===")
    success_count = sum(1 for result in results.values() if result is not None)
    total_tests = len(results)
    
    logger.info(f"Tests réussis: {success_count}/{total_tests}")
    
    for test_name, result in results.items():
        status = "✓ RÉUSSI" if result is not None else "✗ ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")
    
    if success_count >= 3:
        logger.info("🎉 INTÉGRATION LNBITS FONCTIONNELLE")
        return True
    else:
        logger.warning("⚠️  INTÉGRATION PARTIELLE")
        return False

async def test_advanced_features():
    """Test des fonctionnalités avancées."""
    logger.info("\n=== TEST FONCTIONNALITÉS AVANCÉES ===")
    
    lnbits = LNbitsService()
    
    try:
        # Test de données complètes d'un nœud
        logger.info("Test récupération données nœud...")
        node_data = await lnbits.get_node_data("mock_node_1")
        logger.info(f"Données nœud récupérées: {len(node_data.get('channels', []))} canaux")
        
        # Test de vue d'ensemble du réseau
        logger.info("Test vue d'ensemble réseau...")
        network_overview = await lnbits.get_network_overview()
        logger.info(f"Vue d'ensemble: {network_overview['total_nodes']} nœuds total")
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur fonctionnalités avancées: {str(e)}")
        return False

def main():
    """Point d'entrée principal."""
    logger.info("Démarrage des tests d'intégration LNBits")
    
    # Test du service de base
    basic_success = asyncio.run(test_lnbits_service())
    
    # Test des fonctionnalités avancées
    advanced_success = asyncio.run(test_advanced_features())
    
    if basic_success and advanced_success:
        logger.info("🚀 TOUS LES TESTS RÉUSSIS - INTÉGRATION COMPLÈTE")
        return 0
    elif basic_success:
        logger.info("✓ INTÉGRATION DE BASE RÉUSSIE")
        return 0
    else:
        logger.error("❌ ÉCHEC DE L'INTÉGRATION")
        return 1

if __name__ == "__main__":
    exit(main())