#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de rapport Daznode utilisant les données publiques de Mempool.space
"""

import os
import sys
import json
import requests
from datetime import datetime

# Configuration
FEUSTEY_NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5253984937")

def get_node_info():
    """Récupère les informations du nœud depuis Mempool.space"""
    url = f"https://mempool.space/api/v1/lightning/nodes/{FEUSTEY_NODE_ID}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Erreur récupération données: {e}")
    return None

def format_satoshis(sats):
    """Formate les satoshis en BTC"""
    if sats >= 100_000_000:
        return f"{sats / 100_000_000:.2f} BTC"
    elif sats >= 1_000_000:
        return f"{sats / 1_000_000:.2f}M sats"
    elif sats >= 1_000:
        return f"{sats / 1_000:.1f}K sats"
    return f"{sats} sats"

def generate_report():
    """Génère le rapport Daznode"""
    node_data = get_node_info()
    
    if not node_data:
        return "❌ Impossible de récupérer les données du nœud"
    
    # Calcul du statut
    active_channels = node_data.get("active_channel_count", 0)
    total_channels = node_data.get("channel_count", 0)
    capacity = int(node_data.get("capacity", 0))
    
    if active_channels >= 20:
        status = "🟢 EXCELLENT"
    elif active_channels >= 10:
        status = "🟡 BON"
    else:
        status = "🔴 À AMÉLIORER"
    
    # Génération du rapport
    report = f"""⚡ **RAPPORT DAZNODE LIGHTNING NETWORK** ⚡
📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}

🏦 **INFORMATIONS DU NŒUD**
• Alias: {node_data.get('alias', 'Daznode')}
• Statut: {status}
• Node ID: {FEUSTEY_NODE_ID[:16]}...

📊 **MÉTRIQUES RÉSEAU**
• Canaux actifs: {active_channels}/{total_channels} ({(active_channels/max(total_channels,1)*100):.1f}%)
• Capacité totale: {format_satoshis(capacity)}
• Capacité moyenne: {format_satoshis(capacity // max(total_channels, 1))}

💰 **ANALYSE DE LIQUIDITÉ**
• Liquidité entrante estimée: {format_satoshis(capacity // 2)}
• Liquidité sortante estimée: {format_satoshis(capacity // 2)}
• Ratio d'équilibre: ~50%

🎯 **RECOMMANDATIONS**
"""
    
    if active_channels < 10:
        report += "• ⚠️ Augmenter le nombre de canaux actifs (cible: 20+)\n"
    if capacity < 50_000_000:
        report += "• ⚠️ Augmenter la capacité totale (cible: 0.5 BTC+)\n"
    if active_channels >= 10 and capacity >= 50_000_000:
        report += "• ✅ Performance optimale, continuer ainsi!\n"
    
    report += f"""
🔗 **LIENS UTILES**
• [Explorer Mempool](https://mempool.space/lightning/node/{FEUSTEY_NODE_ID})
• [1ML](https://1ml.com/node/{FEUSTEY_NODE_ID})

📈 **Prochain rapport**: Demain 7h00"""
    
    return report

def send_to_telegram(message):
    """Envoie le message sur Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Rapport envoyé sur Telegram avec succès!")
            return True
        else:
            print(f"❌ Erreur envoi Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Exception envoi Telegram: {e}")
    return False

def main():
    print("🚀 Génération du rapport Daznode...")
    print("=" * 50)
    
    # Récupération des données
    print("📊 Collecte des données depuis Mempool.space...")
    report = generate_report()
    
    # Affichage du rapport
    print("\n📄 RAPPORT GÉNÉRÉ:")
    print("-" * 40)
    print(report.replace("**", ""))
    print("-" * 40)
    
    # Envoi sur Telegram
    print("\n📨 Envoi sur Telegram...")
    if send_to_telegram(report):
        print("✅ Rapport Daznode envoyé avec succès!")
    else:
        print("❌ Échec de l'envoi du rapport")

if __name__ == "__main__":
    main()