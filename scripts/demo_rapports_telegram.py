#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de démonstration des rapports Telegram MCP
Affiche le contenu des rapports sans les envoyer
"""

import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configuration de test
os.environ["API_BASE_URL"] = "http://localhost:8000"
os.environ["TELEGRAM_BOT_TOKEN"] = "DEMO_MODE"
os.environ["TELEGRAM_CHAT_ID"] = "DEMO_MODE"

async def demo_rapport_daznode():
    """Démonstration du rapport Daznode"""
    print("🏦 DÉMONSTRATION - RAPPORT DAZNODE")
    print("=" * 50)
    
    try:
        from scripts.daily_daznode_report import DaznodeReporter
        
        reporter = DaznodeReporter()
        
        # Collecter les données (simulation)
        print("📊 Collecte des données du nœud Lightning...")
        node_data = await reporter.get_node_data()
        
        # Formater le rapport
        print("📝 Génération du rapport formaté...")
        report = reporter.format_report(node_data)
        
        print("\n🎯 CONTENU DU RAPPORT DAZNODE:")
        print("-" * 40)
        # Nettoyer le HTML pour l'affichage console
        clean_report = report.replace('<b>', '**').replace('</b>', '**')
        clean_report = clean_report.replace('<i>', '_').replace('</i>', '_')
        print(clean_report)
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Erreur dans la démonstration Daznode: {str(e)}")

async def demo_rapport_sante():
    """Démonstration du rapport de santé"""
    print("\n🏥 DÉMONSTRATION - RAPPORT SANTÉ APPLICATION")
    print("=" * 50)
    
    try:
        from scripts.daily_app_health_report import AppHealthReporter
        
        reporter = AppHealthReporter()
        
        # Collecter les métriques
        print("📊 Collecte des métriques système...")
        system_metrics = await reporter.get_system_metrics()
        
        print("🔗 Test des métriques API...")
        api_metrics = await reporter.get_api_health_metrics()
        
        print("⚡ Test des endpoints (premiers 5)...")
        # Limiter aux 5 premiers endpoints pour la démo
        original_endpoints = reporter.endpoints_to_monitor.copy()
        reporter.endpoints_to_monitor = reporter.endpoints_to_monitor[:5]
        endpoints_test = await reporter.test_all_endpoints()
        reporter.endpoints_to_monitor = original_endpoints
        
        # Formater le rapport
        print("📝 Génération du rapport formaté...")
        report = reporter.format_health_report(system_metrics, api_metrics, endpoints_test)
        
        print("\n🎯 CONTENU DU RAPPORT SANTÉ:")
        print("-" * 40)
        # Nettoyer le HTML pour l'affichage console
        clean_report = report.replace('<b>', '**').replace('</b>', '**')
        clean_report = clean_report.replace('<i>', '_').replace('</i>', '_')
        print(clean_report)
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Erreur dans la démonstration santé: {str(e)}")

async def main():
    """Fonction principale de démonstration"""
    print("🚀 DÉMONSTRATION DES RAPPORTS QUOTIDIENS MCP")
    print("📅", datetime.now().strftime('%d/%m/%Y à %H:%M'))
    print("=" * 60)
    
    print("\n💡 Cette démonstration affiche le contenu des rapports")
    print("   sans les envoyer sur Telegram pour vérifier leur format.")
    print("\n⏳ Démarrage des tests...\n")
    
    # Démonstration du rapport Daznode
    await demo_rapport_daznode()
    
    # Démonstration du rapport de santé
    await demo_rapport_sante()
    
    print("\n✅ DÉMONSTRATION TERMINÉE")
    print("\n📋 RÉSUMÉ:")
    print("• 🏦 Rapport Daznode : KPI du nœud Lightning Network")
    print("• 🏥 Rapport Santé : Métriques système et endpoints API")
    print("\n📧 Pour envoyer sur Telegram, configurez:")
    print("   TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID")
    print("\n⏰ Planification automatique:")
    print("   ./scripts/install_daily_reports_cron.sh")

if __name__ == "__main__":
    asyncio.run(main())