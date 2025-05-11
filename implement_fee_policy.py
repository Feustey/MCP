#!/usr/bin/env python3
import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire courant au path pour les imports
sys.path.append(os.path.abspath("."))

try:
    from src.clients.lnbits_client import LNbitsClient
    from src.api.fee_policy import FeePolicyManager
    from src.api.channel_manager import ChannelManager
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Impossible d'importer les modules nécessaires.")
    sys.exit(1)

NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

class NodeOptimizer:
    """Classe pour optimiser un nœud Lightning selon les recommandations d'analyse"""
    
    def __init__(self, node_id):
        self.node_id = node_id
        # Charger les variables d'environnement depuis .env
        self._load_env()
        self.lnbits_client = LNbitsClient(
            url=os.getenv("LNBITS_URL"),
            admin_key=os.getenv("LNBITS_ADMIN_KEY"),
            invoice_key=os.getenv("LNBITS_INVOICE_KEY")
        )
        self.fee_manager = FeePolicyManager(self.lnbits_client)
        self.channel_manager = ChannelManager(self.lnbits_client)
        
    def _load_env(self):
        """Charger les variables d'environnement depuis .env"""
        from dotenv import load_dotenv
        load_dotenv()
        
    def _load_node_data(self):
        """Charger les données du nœud à partir des fichiers JSON"""
        # Trouver le fichier le plus récent
        node_data_dir = Path(f"rag/RAG_assets/nodes/{self.node_id[:8]}/raw_data")
        if not node_data_dir.exists():
            node_data_dir = Path(f"rag/RAG_assets/nodes/{self.node_id}/raw_data")
            
        if not node_data_dir.exists():
            raise FileNotFoundError(f"Aucun répertoire de données trouvé pour le nœud {self.node_id}")
            
        files = list(node_data_dir.glob("*.json"))
        if not files:
            raise FileNotFoundError(f"Aucun fichier de données trouvé pour le nœud {self.node_id}")
            
        # Trier par date de modification (le plus récent en premier)
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        # Charger les données
        with open(latest_file, "r") as f:
            return json.load(f)

    async def optimize_fee_policy(self):
        """Optimiser la politique de frais selon les recommandations"""
        node_data = self._load_node_data()
        channels = node_data.get("channels", {}).get("channels", [])
        
        if not channels:
            print("Aucun canal trouvé dans les données du nœud.")
            return
            
        print(f"Optimisation de la politique de frais pour {len(channels)} canaux...")
        
        # Classification des canaux
        major_hubs = ["ACINQ", "LNBig", "Wallet of Satoshi", "Bitrefill", "River Financial"]
        regional_nodes = ["RandomNode_6", "RandomNode_7", "RandomNode_8", "RandomNode_9", "RandomNode_10"]
        specialized_services = ["RandomNode_11", "RandomNode_12", "RandomNode_13"]
        volume_channels = ["RandomNode_14", "RandomNode_15", "RandomNode_16", "RandomNode_17", "RandomNode_18"]
        
        optimized_channels = []
        
        for channel in channels:
            channel_type = self._classify_channel(channel, major_hubs, regional_nodes, specialized_services, volume_channels)
            new_policy = self._get_optimized_policy(channel_type)
            
            # Conserver l'ancienne politique pour référence
            old_policy = {
                "fee_rate": channel.get("fee_rate", 0),
                "base_fee": channel.get("base_fee", 0)
            }
            
            optimized_channels.append({
                "channel_id": f"{self.node_id}:{channel['remote_pubkey']}",
                "remote_alias": channel.get("alias", "Unknown"),
                "remote_pubkey": channel["remote_pubkey"],
                "capacity": channel.get("capacity", 0),
                "old_policy": old_policy,
                "new_policy": new_policy,
                "channel_type": channel_type
            })
        
        # Appliquer les nouvelles politiques
        for channel in optimized_channels:
            success = await self.fee_manager.update_channel_policy(
                channel_id=channel["channel_id"],
                fee_rate=channel["new_policy"]["fee_rate_out"],
                base_fee_msat=channel["new_policy"]["base_fee"],
                fee_rate_in=channel["new_policy"]["fee_rate_in"]
            )
            
            status = "✅ Réussi" if success else "❌ Échec"
            print(f"{status} - Mise à jour de la politique pour {channel['remote_alias']} ({channel['channel_type']})")
            print(f"  Ancien: {channel['old_policy']['fee_rate']} ppm, {channel['old_policy']['base_fee']} msats")
            print(f"  Nouveau: {channel['new_policy']['fee_rate_out']} ppm (sortant), {channel['new_policy']['fee_rate_in']} ppm (entrant), {channel['new_policy']['base_fee']} msats")
            
        return optimized_channels
        
    def _classify_channel(self, channel, major_hubs, regional_nodes, specialized_services, volume_channels):
        """Classifier un canal selon son type"""
        alias = channel.get("alias", "")
        
        if alias in major_hubs:
            return "major_hub"
        elif alias in regional_nodes:
            return "regional_node"
        elif alias in specialized_services:
            return "specialized_service"
        elif alias in volume_channels:
            return "volume_channel"
        else:
            # Classification basée sur la capacité
            capacity = channel.get("capacity", 0)
            if capacity > 3000000:
                return "major_hub"
            elif capacity > 2000000:
                return "regional_node"
            elif capacity > 1000000:
                return "specialized_service"
            else:
                return "volume_channel"
    
    def _get_optimized_policy(self, channel_type):
        """Obtenir la politique optimisée en fonction du type de canal"""
        policies = {
            "major_hub": {
                "fee_rate_in": 170,   # 150-180 ppm
                "fee_rate_out": 70,   # 60-75 ppm
                "base_fee": 600       # 600 msats
            },
            "regional_node": {
                "fee_rate_in": 130,   # 120-140 ppm
                "fee_rate_out": 50,   # 45-55 ppm
                "base_fee": 700       # 700 msats
            },
            "specialized_service": {
                "fee_rate_in": 110,   # 100-120 ppm
                "fee_rate_out": 40,   # 35-45 ppm
                "base_fee": 800       # 800 msats
            },
            "volume_channel": {
                "fee_rate_in": 90,    # 80-100 ppm
                "fee_rate_out": 30,   # 25-35 ppm
                "base_fee": 500       # 500 msats
            }
        }
        
        return policies.get(channel_type, policies["regional_node"])
    
    async def open_recommended_channel(self):
        """Ouvrir un canal recommandé avec Breez"""
        target_node = {
            "pubkey": "02d96eadea3d780104449aca5c93461ce67c1564e2e1d73225fa67dd3b997a919f",
            "alias": "Breez",
            "capacity": 2000000  # 2M sats comme recommandé
        }
        
        print(f"Ouverture d'un nouveau canal avec {target_node['alias']} ({target_node['pubkey'][:8]}...)")
        print(f"Capacité: {target_node['capacity']} sats")
        
        # Vérifier le solde disponible
        wallet_info = await self.lnbits_client.get_wallet_details()
        balance = wallet_info.get("balance", 0)
        
        if balance < target_node["capacity"]:
            print(f"⚠️ Solde insuffisant: {balance} sats disponibles, {target_node['capacity']} sats nécessaires.")
            return False
        
        # Ouvrir le canal
        success = await self.channel_manager.open_channel(
            peer_pubkey=target_node["pubkey"],
            local_amt=target_node["capacity"],
            push_amt=0,  # Pas de push initial
            is_private=False,
            sat_per_byte=2  # Frais de transaction raisonnables
        )
        
        if success:
            print(f"✅ Canal ouvert avec succès vers {target_node['alias']}")
            
            # Définir la politique de frais pour le nouveau canal
            channel_id = f"{self.node_id}:{target_node['pubkey']}"
            policy = self._get_optimized_policy("specialized_service")
            
            await self.fee_manager.update_channel_policy(
                channel_id=channel_id,
                fee_rate=policy["fee_rate_out"],
                base_fee_msat=policy["base_fee"],
                fee_rate_in=policy["fee_rate_in"]
            )
            
            print(f"✅ Politique de frais appliquée au nouveau canal: {policy['fee_rate_out']} ppm (sortant), {policy['fee_rate_in']} ppm (entrant), {policy['base_fee']} msats")
        else:
            print(f"❌ Échec de l'ouverture du canal vers {target_node['alias']}")
        
        return success
    
    async def generate_recommendations_report(self, optimized_channels):
        """Générer un rapport de recommandations après optimisation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path(f"data/reports/{self.node_id[:8]}")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"{timestamp}_fee_policy_optimization.md"
        
        with open(report_file, "w") as f:
            f.write(f"# Rapport d'optimisation du nœud {self.node_id[:8]}\n\n")
            f.write(f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Politique de frais optimisée\n\n")
            f.write("| Alias | Type | Capacité | Ancienne politique | Nouvelle politique |\n")
            f.write("|-------|------|----------|-------------------|-------------------|\n")
            
            for channel in optimized_channels:
                f.write(f"| {channel['remote_alias']} | {channel['channel_type']} | {channel['capacity']} | ")
                f.write(f"{channel['old_policy']['fee_rate']} ppm, {channel['old_policy']['base_fee']} msats | ")
                f.write(f"{channel['new_policy']['fee_rate_out']}/{channel['new_policy']['fee_rate_in']} ppm, {channel['new_policy']['base_fee']} msats |\n")
            
            f.write("\n## Résumé des optimisations\n\n")
            f.write(f"- {len(optimized_channels)} canaux ont été optimisés\n")
            f.write("- Stratégie multi-dimensionnelle appliquée\n")
            f.write("- Alignement avec les recommandations de l'analyse du nœud\n\n")
            
            f.write("## Prochaines étapes recommandées\n\n")
            f.write("1. Surveiller les performances pendant 7 jours\n")
            f.write("2. Ouvrir des canaux supplémentaires vers Podcast Index et BTCPay Server\n")
            f.write("3. Mettre en place une politique d'équilibrage automatique\n")
            f.write("4. Configurer des alertes pour les déséquilibres importants\n")
        
        print(f"✅ Rapport généré: {report_file}")
        return str(report_file)

async def main():
    """Fonction principale"""
    try:
        optimizer = NodeOptimizer(NODE_ID)
        
        # Optimiser la politique de frais
        print("=== OPTIMISATION DE LA POLITIQUE DE FRAIS ===")
        optimized_channels = await optimizer.optimize_fee_policy()
        
        # Ouvrir un nouveau canal recommandé
        print("\n=== OUVERTURE D'UN NOUVEAU CANAL ===")
        await optimizer.open_recommended_channel()
        
        # Générer un rapport de recommandations
        print("\n=== GÉNÉRATION DU RAPPORT ===")
        report_file = await optimizer.generate_recommendations_report(optimized_channels)
        
        print("\n✅ Optimisation terminée avec succès.")
        print(f"Le rapport est disponible ici: {report_file}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'optimisation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 