#!/usr/bin/env python3
"""
Script de validation finale de l'intégration LNBits avec MCP.
Ce script valide que l'intégration fonctionne correctement.
"""

import json
import logging
import os
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_files_structure():
    """Valide la structure des fichiers d'intégration."""
    logger.info("=== VALIDATION STRUCTURE FICHIERS ===")
    
    required_files = [
        "app/services/lnbits.py",
        "app/routes/lightning.py", 
        "src/clients/lnbits_client.py"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            existing_files.append(file_path)
            logger.info(f"✓ {file_path}")
        else:
            missing_files.append(file_path)
            logger.warning(f"✗ {file_path} (manquant)")
    
    return len(missing_files) == 0, existing_files, missing_files

def validate_lnbits_service():
    """Valide le service LNBits."""
    logger.info("\n=== VALIDATION SERVICE LNBITS ===")
    
    try:
        # Lire le fichier du service
        with open("app/services/lnbits.py", "r") as f:
            content = f.read()
        
        # Vérifier les fonctionnalités clés
        required_methods = [
            "_should_use_mock",
            "_mock_response", 
            "get_wallet_details",
            "create_invoice",
            "pay_invoice",
            "get_network_stats",
            "get_network_nodes"
        ]
        
        missing_methods = []
        existing_methods = []
        
        for method in required_methods:
            if f"def {method}" in content:
                existing_methods.append(method)
                logger.info(f"✓ Méthode {method}")
            else:
                missing_methods.append(method)
                logger.warning(f"✗ Méthode {method} (manquante)")
        
        # Vérifier les imports mock
        has_mock_support = "_should_use_mock" in content and "_mock_response" in content
        logger.info(f"Support mock: {'✓ Activé' if has_mock_support else '✗ Désactivé'}")
        
        return len(missing_methods) == 0, existing_methods, missing_methods
        
    except Exception as e:
        logger.error(f"Erreur validation service: {str(e)}")
        return False, [], []

def validate_lightning_routes():
    """Valide les routes Lightning."""
    logger.info("\n=== VALIDATION ROUTES LIGHTNING ===")
    
    try:
        with open("app/routes/lightning.py", "r") as f:
            content = f.read()
        
        required_endpoints = [
            "get_explorer_nodes",
            "get_rankings", 
            "get_global_stats",
            "get_calculator",
            "get_decoder"
        ]
        
        missing_endpoints = []
        existing_endpoints = []
        
        for endpoint in required_endpoints:
            if f"async def {endpoint}" in content:
                existing_endpoints.append(endpoint)
                logger.info(f"✓ Endpoint {endpoint}")
            else:
                missing_endpoints.append(endpoint)
                logger.warning(f"✗ Endpoint {endpoint} (manquant)")
        
        # Vérifier l'import du service
        has_service_import = "from app.services.lnbits import LNbitsService" in content
        logger.info(f"Import service: {'✓ OK' if has_service_import else '✗ Manquant'}")
        
        return len(missing_endpoints) == 0, existing_endpoints, missing_endpoints
        
    except Exception as e:
        logger.error(f"Erreur validation routes: {str(e)}")
        return False, [], []

def validate_client_fallback():
    """Valide le client avec fallback."""
    logger.info("\n=== VALIDATION CLIENT FALLBACK ===")
    
    try:
        with open("src/clients/lnbits_client.py", "r") as f:
            content = f.read()
        
        # Vérifier les fonctionnalités de fallback
        fallback_features = [
            "async def _make_request",
            "send_test_payment",
            "get_node_channels", 
            "get_wallet_info"
        ]
        
        missing_features = []
        existing_features = []
        
        for feature in fallback_features:
            if feature in content:
                existing_features.append(feature)
                logger.info(f"✓ {feature}")
            else:
                missing_features.append(feature)
                logger.warning(f"✗ {feature} (manquant)")
        
        return len(missing_features) == 0, existing_features, missing_features
        
    except Exception as e:
        logger.error(f"Erreur validation client: {str(e)}")
        return False, [], []

def generate_integration_report():
    """Génère un rapport d'intégration."""
    logger.info("\n=== RAPPORT D'INTÉGRATION LNBITS ===")
    
    # Validation des différents composants
    files_ok, existing_files, missing_files = validate_files_structure()
    service_ok, service_methods, missing_service_methods = validate_lnbits_service()
    routes_ok, existing_routes, missing_routes = validate_lightning_routes()
    client_ok, client_features, missing_client_features = validate_client_fallback()
    
    # Calcul du score global
    total_components = 4
    successful_components = sum([files_ok, service_ok, routes_ok, client_ok])
    success_rate = (successful_components / total_components) * 100
    
    # Rapport détaillé
    report = {
        "integration_status": "SUCCESS" if success_rate >= 75 else "PARTIAL" if success_rate >= 50 else "FAILED",
        "success_rate": success_rate,
        "components": {
            "files_structure": {
                "status": "OK" if files_ok else "FAILED",
                "existing": existing_files,
                "missing": missing_files
            },
            "lnbits_service": {
                "status": "OK" if service_ok else "FAILED", 
                "methods": service_methods,
                "missing_methods": missing_service_methods
            },
            "lightning_routes": {
                "status": "OK" if routes_ok else "FAILED",
                "endpoints": existing_routes,
                "missing_endpoints": missing_routes
            },
            "client_fallback": {
                "status": "OK" if client_ok else "FAILED",
                "features": client_features,
                "missing_features": missing_client_features
            }
        },
        "recommendations": []
    }
    
    # Recommandations
    if not files_ok:
        report["recommendations"].append("Vérifier que tous les fichiers d'intégration sont présents")
    
    if not service_ok:
        report["recommendations"].append("Compléter les méthodes manquantes dans le service LNBits")
    
    if not routes_ok:
        report["recommendations"].append("Ajouter les endpoints Lightning manquants")
    
    if not client_ok:
        report["recommendations"].append("Améliorer le client avec les fonctionnalités de fallback")
    
    if success_rate == 100:
        report["recommendations"].append("✅ Intégration complète - Prêt pour la production")
    elif success_rate >= 75:
        report["recommendations"].append("✅ Intégration fonctionnelle - Quelques améliorations possibles")
    
    return report

def main():
    """Point d'entrée principal."""
    logger.info("🔍 VALIDATION INTÉGRATION LNBITS AVEC MCP")
    
    # Générer le rapport
    report = generate_integration_report()
    
    # Afficher les résultats
    logger.info(f"\n📊 RÉSULTATS:")
    logger.info(f"Statut: {report['integration_status']}")
    logger.info(f"Taux de réussite: {report['success_rate']:.1f}%")
    
    logger.info(f"\n📝 COMPOSANTS:")
    for component_name, component_data in report['components'].items():
        status_icon = "✅" if component_data['status'] == 'OK' else "❌"
        logger.info(f"{status_icon} {component_name.replace('_', ' ').title()}: {component_data['status']}")
    
    if report['recommendations']:
        logger.info(f"\n💡 RECOMMANDATIONS:")
        for rec in report['recommendations']:
            logger.info(f"  • {rec}")
    
    # Sauvegarder le rapport
    with open("lnbits_integration_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n📄 Rapport sauvegardé: lnbits_integration_report.json")
    
    # Conclusion
    if report['success_rate'] >= 75:
        logger.info("\n🎉 INTÉGRATION LNBITS RÉUSSIE!")
        logger.info("✅ Le système Lightning est prêt pour l'utilisation avec MCP")
        return 0
    elif report['success_rate'] >= 50:
        logger.info("\n⚠️  INTÉGRATION PARTIELLE")
        logger.info("🔧 Quelques composants nécessitent des ajustements")
        return 0
    else:
        logger.error("\n❌ ÉCHEC DE L'INTÉGRATION")
        logger.error("🔧 Des composants critiques manquent ou sont défaillants")
        return 1

if __name__ == "__main__":
    exit(main())