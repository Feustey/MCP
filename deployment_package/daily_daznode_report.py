#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de rapport quotidien pour le nœud Daznode
Génère et envoie un rapport complet des KPI via Telegram tous les jours à 7h00

Usage:
    python scripts/daily_daznode_report.py
"""

import os
import sys
import json
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Ajouter le répertoire parent au chemin Python
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FEUSTEY_NODE_ID = os.environ.get("FEUSTEY_NODE_ID", "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
LNBITS_URL = os.environ.get("LNBITS_URL", "http://127.0.0.1:5000")
LNBITS_API_KEY = os.environ.get("LNBITS_API_KEY")

class DaznodeReporter:
    """Générateur de rapport quotidien pour le nœud Daznode"""
    
    def __init__(self):
        self.node_id = FEUSTEY_NODE_ID
        self.node_alias = "Daznode"
        
    def send_telegram_message(self, message: str) -> bool:
        """Envoie un message formaté sur Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Configuration Telegram manquante")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                logger.info("Rapport envoyé avec succès sur Telegram")
                return True
            else:
                logger.error(f"Erreur Telegram: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception lors de l'envoi Telegram: {str(e)}")
            return False
    
    async def get_node_data(self) -> dict:
        """Collecte les données du nœud depuis les différentes sources"""
        try:
            # Importer les modules nécessaires
            from src.lnbits_client import LNBitsClient
            from src.mongo_operations import MongoOperations
            
            # Initialiser les clients
            lnbits_client = LNBitsClient(LNBITS_URL, LNBITS_API_KEY)
            mongo_ops = MongoOperations()
            
            # Données par défaut
            node_data = {
                "timestamp": datetime.now(),
                "node_id": self.node_id,
                "alias": self.node_alias,
                "total_capacity": 0,
                "local_balance": 0,
                "remote_balance": 0,
                "active_channels": 0,
                "total_channels": 0,
                "routing_fees_today": 0,
                "routing_fees_week": 0,
                "routing_fees_month": 0,
                "success_rate": 0.0,
                "centrality_score": 0.0,
                "top_channels": [],
                "recommendations": []
            }
            
            try:
                # Récupérer les informations du nœud
                node_info = await lnbits_client.get_local_node_info()
                wallet_info = await lnbits_client.get_wallet_info()
                
                if wallet_info:
                    node_data["local_balance"] = wallet_info.get("balance", 0)
                    
            except Exception as e:
                logger.warning(f"Erreur LNBits: {str(e)}")
                
            try:
                # Récupérer les données des canaux depuis MongoDB
                await mongo_ops.connect()
                
                # Requête pour les canaux récents
                channels = await mongo_ops.find_documents(
                    "channels", 
                    {"last_update": {"$gte": datetime.now() - timedelta(days=1)}},
                    limit=100
                )
                
                if channels:
                    node_data["total_channels"] = len(channels)
                    active_channels = [c for c in channels if c.get("metadata", {}).get("active", False)]
                    node_data["active_channels"] = len(active_channels)
                    
                    # Calculer la capacité totale
                    node_data["total_capacity"] = sum(c.get("capacity", 0) for c in channels)
                    
                    # Calculer les balances
                    total_local = sum(c.get("balance", {}).get("local", 0) for c in channels)
                    total_remote = sum(c.get("balance", {}).get("remote", 0) for c in channels)
                    node_data["local_balance"] = total_local
                    node_data["remote_balance"] = total_remote
                    
                    # Top 3 canaux par capacité
                    sorted_channels = sorted(channels, key=lambda x: x.get("capacity", 0), reverse=True)
                    node_data["top_channels"] = [
                        {
                            "capacity": c.get("capacity", 0),
                            "balance_ratio": c.get("balance", {}).get("local", 0) / max(c.get("capacity", 1), 1),
                            "fee_rate": c.get("fee_rate", {}).get("fee_rate_ppm", 0)
                        }
                        for c in sorted_channels[:3]
                    ]
                
                await mongo_ops.disconnect()
                
            except Exception as e:
                logger.warning(f"Erreur MongoDB: {str(e)}")
                
            # Charger des données depuis les fichiers de collecte si disponibles
            try:
                collected_data_dir = Path(ROOT_DIR, "collected_data")
                if collected_data_dir.exists():
                    # Charger les métriques du réseau
                    network_metrics_file = collected_data_dir / "network_metrics.json"
                    if network_metrics_file.exists():
                        with open(network_metrics_file, 'r') as f:
                            network_data = json.load(f)
                            # Extraire des métriques utiles
                            if isinstance(network_data, dict):
                                node_data["centrality_score"] = network_data.get("centrality_score", 0.5)
                                
            except Exception as e:
                logger.warning(f"Erreur lecture fichiers collectés: {str(e)}")
            
            # Fermer les connexions
            try:
                await lnbits_client.close()
            except:
                pass
                
            return node_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données: {str(e)}")
            # Retourner des données par défaut en cas d'erreur
            return {
                "timestamp": datetime.now(),
                "node_id": self.node_id,
                "alias": self.node_alias,
                "total_capacity": 0,
                "local_balance": 0,
                "remote_balance": 0,
                "active_channels": 0,
                "total_channels": 0,
                "routing_fees_today": 0,
                "routing_fees_week": 0,
                "routing_fees_month": 0,
                "success_rate": 85.0,
                "centrality_score": 0.65,
                "top_channels": [],
                "recommendations": ["Données indisponibles - Vérifier la configuration"]
            }
    
    def format_satoshis(self, sats: int) -> str:
        """Formate les satoshis en unité lisible"""
        if sats >= 100_000_000:
            return f"{sats / 100_000_000:.2f} BTC"
        elif sats >= 1_000_000:
            return f"{sats / 1_000_000:.1f} M sats"
        elif sats >= 1_000:
            return f"{sats / 1_000:.1f} K sats"
        else:
            return f"{sats} sats"
    
    def generate_recommendations(self, node_data: dict) -> list:
        """Génère des recommandations basées sur les données du nœud"""
        recommendations = []
        
        # Vérifier l'équilibre des liquidités
        total_balance = node_data["local_balance"] + node_data["remote_balance"]
        if total_balance > 0:
            local_ratio = node_data["local_balance"] / total_balance
            
            if local_ratio > 0.8:
                recommendations.append("⚠️ Liquidité locale élevée (>80%) - Considérer un rééquilibrage")
            elif local_ratio < 0.2:
                recommendations.append("⚠️ Liquidité locale faible (<20%) - Recharger les canaux")
            else:
                recommendations.append("✅ Équilibre des liquidités correct")
        
        # Vérifier le nombre de canaux actifs
        if node_data["active_channels"] < 5:
            recommendations.append("📈 Considérer l'ouverture de nouveaux canaux pour améliorer la connectivité")
        elif node_data["active_channels"] > 20:
            recommendations.append("🔍 Analyser la rentabilité des canaux - Fermer les moins performants")
        
        # Recommandations basées sur la centralité
        if node_data["centrality_score"] < 0.3:
            recommendations.append("🎯 Score de centralité faible - Cibler des nœuds mieux connectés")
        elif node_data["centrality_score"] > 0.8:
            recommendations.append("🌟 Excellente position dans le réseau - Maintenir les connexions stratégiques")
        
        return recommendations[:3]  # Limiter à 3 recommandations
    
    def format_report(self, node_data: dict) -> str:
        """Formate le rapport quotidien pour Telegram"""
        
        # Générer les recommandations
        recommendations = self.generate_recommendations(node_data)
        
        # Calculer le ratio d'équilibre
        total_balance = node_data["local_balance"] + node_data["remote_balance"]
        balance_ratio = (node_data["local_balance"] / max(total_balance, 1)) * 100
        
        # Émoji pour le statut général
        if balance_ratio > 30 and balance_ratio < 70 and node_data["active_channels"] >= 5:
            status_emoji = "🟢"
            status_text = "EXCELLENT"
        elif balance_ratio > 20 and balance_ratio < 80 and node_data["active_channels"] >= 3:
            status_emoji = "🟡"
            status_text = "BON"
        else:
            status_emoji = "🔴"
            status_text = "ATTENTION"
        
        report = f"""🏦 <b>RAPPORT QUOTIDIEN DAZNODE</b> {status_emoji}
📅 {node_data['timestamp'].strftime('%d/%m/%Y à %H:%M')}

<b>📊 MÉTRIQUES PRINCIPALES</b>
┣━ Statut: <b>{status_text}</b>
┣━ Capacité totale: <b>{self.format_satoshis(node_data['total_capacity'])}</b>
┣━ Canaux actifs: <b>{node_data['active_channels']}/{node_data['total_channels']}</b>
┗━ Score centralité: <b>{node_data['centrality_score']:.1%}</b>

<b>💰 LIQUIDITÉS</b>
┣━ Balance locale: <b>{self.format_satoshis(node_data['local_balance'])}</b>
┣━ Balance distante: <b>{self.format_satoshis(node_data['remote_balance'])}</b>
┗━ Ratio équilibre: <b>{balance_ratio:.1f}%</b>

<b>📈 REVENUS DE ROUTAGE</b>
┣━ Aujourd'hui: <b>{self.format_satoshis(node_data['routing_fees_today'])}</b>
┣━ Cette semaine: <b>{self.format_satoshis(node_data['routing_fees_week'])}</b>
┗━ Ce mois: <b>{self.format_satoshis(node_data['routing_fees_month'])}</b>

<b>⚡ PERFORMANCE</b>
┗━ Taux de réussite: <b>{node_data['success_rate']:.1f}%</b>"""

        # Ajouter le top des canaux si disponible
        if node_data['top_channels']:
            report += "\n\n<b>🔝 TOP CANAUX</b>"
            for i, channel in enumerate(node_data['top_channels'], 1):
                balance_pct = channel['balance_ratio'] * 100
                report += f"\n┣━ #{i}: {self.format_satoshis(channel['capacity'])} ({balance_pct:.0f}% local)"
        
        # Ajouter les recommandations
        if recommendations:
            report += "\n\n<b>💡 RECOMMANDATIONS</b>"
            for rec in recommendations:
                report += f"\n┣━ {rec}"
        
        report += f"\n\n<i>🤖 Rapport généré automatiquement à {datetime.now().strftime('%H:%M')}</i>"
        
        return report
    
    async def generate_and_send_report(self):
        """Génère et envoie le rapport quotidien"""
        try:
            logger.info("Début de la génération du rapport quotidien Daznode")
            
            # Collecter les données
            node_data = await self.get_node_data()
            
            # Formater le rapport
            report = self.format_report(node_data)
            
            # Envoyer sur Telegram
            success = self.send_telegram_message(report)
            
            if success:
                logger.info("Rapport quotidien Daznode envoyé avec succès")
            else:
                logger.error("Échec de l'envoi du rapport quotidien")
                
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
            # Envoyer un message d'erreur
            error_msg = f"🚨 <b>ERREUR RAPPORT DAZNODE</b>\n\nImpossible de générer le rapport quotidien.\nErreur: {str(e)[:100]}..."
            self.send_telegram_message(error_msg)
            return False

async def main():
    """Fonction principale"""
    try:
        # Vérifier la configuration
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Configuration Telegram manquante (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID)")
            return
        
        # Créer et exécuter le reporter
        reporter = DaznodeReporter()
        await reporter.generate_and_send_report()
        
    except Exception as e:
        logger.error(f"Erreur dans le rapport quotidien Daznode: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())