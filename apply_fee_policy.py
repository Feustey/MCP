#!/usr/bin/env python3
import os
import json
from datetime import datetime
from pathlib import Path

# Configuration du nœud
NODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

# Politiques de frais par type de canal
FEE_POLICIES = {
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

# Liste des grands hubs connus
MAJOR_HUBS = [
    "ACINQ",
    "LNBig",
    "Wallet of Satoshi",
    "WalletOfSatoshi.com",
    "Bitrefill",
    "River Financial",
    "Bitfinex",
    "Kraken",
    "OKX",
    "Binance",
    "Boltz Exchange",
    "LN Markets"
]

def load_node_data():
    """Charge les données du nœud depuis le fichier le plus récent"""
    node_data_dir = Path(f"rag/RAG_assets/nodes/{NODE_ID[:8]}/raw_data")
    if not node_data_dir.exists():
        node_data_dir = Path(f"rag/RAG_assets/nodes/{NODE_ID}/raw_data")
        
    if not node_data_dir.exists():
        raise FileNotFoundError(f"Aucun répertoire de données trouvé pour le nœud {NODE_ID}")
        
    files = list(node_data_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier de données trouvé pour le nœud {NODE_ID}")
        
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    
    with open(latest_file, "r") as f:
        return json.load(f)

def clean_number(number_str):
    """Nettoie une chaîne de caractères représentant un nombre"""
    return int(number_str.replace(",", "").replace(" sats", "").replace(" sat", ""))

def classify_channel(channel):
    """Classifie un canal selon son type"""
    alias = channel["remote_node"]["alias"]
    capacity = clean_number(channel["capacity"])
    
    if alias in MAJOR_HUBS or capacity > 2000000:  # > 2M sats
        return "major_hub"
    elif capacity > 1500000:  # > 1.5M sats
        return "regional_node"
    elif capacity > 1000000:  # > 1M sats
        return "specialized_service"
    else:
        return "volume_channel"

def format_channel_point(channel_id):
    """Format du channel_point pour la commande lncli"""
    return f"{channel_id}:0"  # Utilise l'index 0 par défaut

def generate_lncli_commands(channels):
    """Génère les commandes lncli pour mettre à jour les politiques de frais"""
    commands = []
    for channel in channels:
        channel_type = classify_channel(channel)
        policy = FEE_POLICIES[channel_type]
        channel_point = format_channel_point(channel["id"])
        
        # Commande pour mettre à jour la politique sortante
        cmd_out = (
            f"lncli updatechanpolicy --base_fee_msat {policy['base_fee']} "
            f"--fee_rate_ppm {policy['fee_rate_out']} "
            f"--time_lock_delta 40 --chan_point {channel_point}"
        )
        commands.append({
            "type": channel_type,
            "direction": "out",
            "command": cmd_out,
            "alias": channel["remote_node"]["alias"],
            "capacity": clean_number(channel["capacity"]),
            "current_fee_rate": channel.get("fee_rate", "N/A"),
            "current_base_fee": channel.get("base_fee", "N/A"),
            "policy": {
                "base_fee": policy["base_fee"],
                "fee_rate": policy["fee_rate_out"]
            }
        })
        
        # Commande pour mettre à jour la politique entrante
        cmd_in = (
            f"lncli updatechanpolicy --base_fee_msat {policy['base_fee']} "
            f"--fee_rate_ppm {policy['fee_rate_in']} "
            f"--time_lock_delta 40 --chan_point {channel_point}"
        )
        commands.append({
            "type": channel_type,
            "direction": "in",
            "command": cmd_in,
            "alias": channel["remote_node"]["alias"],
            "capacity": clean_number(channel["capacity"]),
            "current_fee_rate": channel.get("fee_rate", "N/A"),
            "current_base_fee": channel.get("base_fee", "N/A"),
            "policy": {
                "base_fee": policy["base_fee"],
                "fee_rate": policy["fee_rate_in"]
            }
        })
    
    return commands

def main():
    try:
        # Charger les données du nœud
        print(f"Chargement des données pour le nœud {NODE_ID[:8]}...")
        node_data = load_node_data()
        
        # Extraire les canaux actifs
        channels = node_data.get("channels", {}).get("active_channels", [])
        if not channels:
            print("Aucun canal actif trouvé.")
            return
            
        print(f"Analyse de {len(channels)} canaux actifs...")
        
        # Générer les commandes
        commands = generate_lncli_commands(channels)
        
        # Créer le fichier de commandes
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("data/actions")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"fee_policy_commands_{timestamp}.sh"
        with open(output_file, "w") as f:
            f.write("#!/bin/bash\n\n")
            f.write("# Script généré automatiquement pour la mise à jour des politiques de frais\n")
            f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for cmd in commands:
                f.write(f"# Canal: {cmd['alias']} ({cmd['capacity']} sats)\n")
                f.write(f"# Type: {cmd['type']} - Direction: {cmd['direction']}\n")
                f.write(f"# Politique actuelle: {cmd['current_fee_rate']}, {cmd['current_base_fee']}\n")
                f.write(f"# Nouvelle politique: {cmd['policy']['fee_rate']} ppm, {cmd['policy']['base_fee']} msats\n")
                f.write(f"{cmd['command']}\n\n")
        
        os.chmod(output_file, 0o755)
        
        print(f"\nScript de commandes généré: {output_file}")
        print("\nRésumé des modifications proposées:")
        
        channel_types = {}
        for cmd in commands:
            if cmd["direction"] == "out":  # Ne compter que les canaux sortants pour éviter les doublons
                channel_type = cmd["type"]
                if channel_type not in channel_types:
                    channel_types[channel_type] = []
                channel_types[channel_type].append(cmd["alias"])
        
        for channel_type, aliases in channel_types.items():
            print(f"\n{channel_type.upper()}:")
            policy = FEE_POLICIES[channel_type]
            print(f"  Frais: {policy['fee_rate_out']}/{policy['fee_rate_in']} ppm, {policy['base_fee']} msats")
            print(f"  Canaux: {', '.join(aliases)}")
        
        print("\nPour appliquer les changements:")
        print(f"1. Vérifiez le contenu du script: cat {output_file}")
        print(f"2. Exécutez le script: {output_file}")
        print("\nATTENTION: Vérifiez bien les commandes avant de les exécuter!")
        
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 