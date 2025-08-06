#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour le rapport quotidien de santé de l'application MCP
Teste la génération et l'envoi du rapport sans planification
"""

import os
import sys
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.daily_app_health_report import AppHealthReporter

async def test_components():
    """Test des composants individuels du reporter"""
    print("🧪 Test des composants du rapport de santé...")
    print("=" * 50)
    
    reporter = AppHealthReporter()
    
    # Test des métriques système
    print("📊 Test des métriques système...")
    system_metrics = await reporter.get_system_metrics()
    print(f"   CPU: {system_metrics.get('cpu_usage', 0):.1f}%")
    print(f"   Mémoire: {system_metrics.get('memory_usage', 0):.1f}%")
    print(f"   Disque: {system_metrics.get('disk_usage', 0):.1f}%")
    
    # Test de l'API
    print("\n🔗 Test des métriques API...")
    api_metrics = await reporter.get_api_health_metrics()
    print(f"   Status API: {api_metrics.get('api_status', 'unknown')}")
    print(f"   Health check: {api_metrics.get('health_check', {}).get('status', 'unknown')}")
    
    # Test d'un endpoint spécifique
    print("\n⚡ Test d'un endpoint...")
    endpoint_result = await reporter.test_endpoint("/health")
    print(f"   /health: {endpoint_result['status']} ({endpoint_result['response_time_ms']}ms)")
    
    # Test de plusieurs endpoints
    print("\n🌐 Test des endpoints critiques...")
    endpoints_test = await reporter.test_all_endpoints()
    print(f"   Endpoints testés: {endpoints_test['total_endpoints']}")
    print(f"   Succès: {endpoints_test['successful_endpoints']}")
    print(f"   Taux de succès: {endpoints_test['success_rate']:.1f}%")
    print(f"   Temps moyen: {endpoints_test['average_response_time']:.0f}ms")
    
    if endpoints_test['error_endpoints']:
        print(f"   Endpoints en erreur: {len(endpoints_test['error_endpoints'])}")
        for error_ep in endpoints_test['error_endpoints'][:3]:
            print(f"     - {error_ep['endpoint']}: {error_ep['status']}")
    
    return system_metrics, api_metrics, endpoints_test

async def test_report_generation():
    """Test de génération du rapport complet"""
    print("\n📝 Test de génération du rapport complet...")
    print("-" * 30)
    
    reporter = AppHealthReporter()
    
    # Générer les données
    system_metrics, api_metrics, endpoints_test = await test_components()
    
    # Générer le rapport formaté
    report = reporter.format_health_report(system_metrics, api_metrics, endpoints_test)
    
    print("📄 Aperçu du rapport:")
    print("-" * 30)
    # Afficher les premières lignes du rapport (sans HTML)
    preview = report.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
    lines = preview.split('\n')[:15]
    for line in lines:
        print(f"   {line}")
    print("   [...] (rapport complet)")
    print("-" * 30)
    
    return report

async def test_full_report():
    """Test du rapport complet avec envoi optionnel"""
    print("\n🚀 Test du rapport complet...")
    
    # Vérifier les variables d'environnement
    required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variables d'environnement manquantes: {', '.join(missing_vars)}")
        print("   Veuillez les définir dans votre fichier .env")
        print("   Test sans envoi Telegram...")
        
        # Générer juste le rapport
        report = await test_report_generation()
        return True
        
    print("✅ Variables d'environnement configurées")
    
    # Générer le rapport complet
    report = await test_report_generation()
    
    # Demander confirmation pour l'envoi
    response = input("\n📨 Envoyer le rapport sur Telegram ? (o/N): ").lower().strip()
    
    if response in ['o', 'oui', 'y', 'yes']:
        print("📤 Envoi du rapport...")
        reporter = AppHealthReporter()
        success = reporter.send_telegram_message(report)
        
        if success:
            print("✅ Rapport envoyé avec succès!")
            return True
        else:
            print("❌ Échec de l'envoi du rapport")
            return False
    else:
        print("📋 Test terminé sans envoi")
        return True

def main():
    """Fonction principale"""
    try:
        print("🏥 Test du Rapport de Santé Application MCP")
        print("=" * 50)
        
        # Vérifier l'URL de l'API
        api_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
        print(f"🔗 URL de l'API: {api_url}")
        
        result = asyncio.run(test_full_report())
        
        if result:
            print("\n🎉 Test réussi!")
            print("\n💡 Pour planifier le rapport quotidien:")
            print("   1. Ajoutez à votre crontab:")
            print("      0 7 * * * cd /path/to/mcp && python3 scripts/daily_app_health_report.py")
            print("   2. Ou utilisez le script d'installation:")
            print("      ./scripts/install_health_cron.sh")
        else:
            print("\n❌ Test échoué - Vérifiez la configuration")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrompu")
    except Exception as e:
        print(f"\n💥 Erreur lors du test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()