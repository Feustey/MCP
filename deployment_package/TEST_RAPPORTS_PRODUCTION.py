#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test en production pour les rapports MCP
Lance les deux rapports et les envoie sur Telegram
"""

import os
import sys
import asyncio
from datetime import datetime

def main():
    """Test des rapports en production"""
    print("🚀 TEST DES RAPPORTS EN PRODUCTION")
    print("📅", datetime.now().strftime('%d/%m/%Y à %H:%M'))
    print("=" * 50)
    
    # Vérifier qu'on est dans le bon répertoire
    if not os.path.exists('scripts/daily_daznode_report.py'):
        print("❌ Erreur: Scripts non trouvés")
        print("   Exécutez ce script depuis /home/feustey/MCP-1/")
        sys.exit(1)
    
    # Vérifier les variables Telegram
    env_file = '.env.production'
    if not os.path.exists(env_file):
        print(f"❌ Fichier {env_file} non trouvé")
        sys.exit(1)
    
    # Lire les variables
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    if 'YOUR_BOT_TOKEN' in env_content or 'YOUR_CHAT_ID' in env_content:
        print("⚠️  ATTENTION: Variables Telegram non configurées")
        print("   Configurez TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID")
        print("   dans .env.production avant de continuer")
        return
    
    print("✅ Configuration trouvée")
    print()
    
    # Test 1: Rapport Daznode
    print("🏦 TEST 1: Rapport Daznode")
    print("-" * 30)
    try:
        os.system("python3 scripts/daily_daznode_report.py")
        print("✅ Rapport Daznode envoyé")
    except Exception as e:
        print(f"❌ Erreur Rapport Daznode: {e}")
    
    print()
    
    # Test 2: Rapport Santé App
    print("🏥 TEST 2: Rapport Santé Application")
    print("-" * 30)
    try:
        os.system("python3 scripts/daily_app_health_report.py")
        print("✅ Rapport Santé envoyé")
    except Exception as e:
        print(f"❌ Erreur Rapport Santé: {e}")
    
    print()
    print("🎯 TEST TERMINÉ")
    print("📱 Vérifiez vos messages Telegram !")
    print()
    print("📊 Vous devriez avoir reçu :")
    print("   🏦 Rapport quotidien Daznode avec KPI Lightning")
    print("   🏥 Rapport santé application avec métriques système")

if __name__ == "__main__":
    main()