#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour le rapport quotidien Daznode
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

from scripts.daily_daznode_report import DaznodeReporter

async def test_report():
    """Test de génération et envoi du rapport"""
    print("🧪 Test du rapport quotidien Daznode...")
    print("=" * 50)
    
    # Vérifier les variables d'environnement
    required_vars = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Variables d'environnement manquantes: {', '.join(missing_vars)}")
        print("   Veuillez les définir dans votre fichier .env")
        return False
        
    print("✅ Variables d'environnement configurées")
    
    # Créer le reporter
    reporter = DaznodeReporter()
    
    # Collecter les données (test)
    print("📊 Collecte des données du nœud...")
    node_data = await reporter.get_node_data()
    
    print(f"   - Node ID: {node_data['node_id'][:16]}...")
    print(f"   - Alias: {node_data['alias']}")
    print(f"   - Canaux actifs: {node_data['active_channels']}/{node_data['total_channels']}")
    print(f"   - Capacité totale: {reporter.format_satoshis(node_data['total_capacity'])}")
    
    # Générer le rapport (test)
    print("📝 Génération du rapport...")
    report = reporter.format_report(node_data)
    
    print("📄 Aperçu du rapport:")
    print("-" * 30)
    # Afficher les premiers lignes du rapport (sans HTML)
    preview = report.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
    lines = preview.split('\n')[:10]
    for line in lines:
        print(f"   {line}")
    print("   [...] (rapport complet)")
    print("-" * 30)
    
    # Demander confirmation pour l'envoi
    response = input("\n📨 Envoyer le rapport sur Telegram ? (o/N): ").lower().strip()
    
    if response in ['o', 'oui', 'y', 'yes']:
        print("📤 Envoi du rapport...")
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
        result = asyncio.run(test_report())
        if result:
            print("\n🎉 Test réussi!")
            print("\n💡 Pour installer la planification automatique:")
            print("   ./scripts/install_daznode_cron.sh")
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