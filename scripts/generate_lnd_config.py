#!/usr/bin/env python3
"""
Script pour générer une configuration LND optimisée pour le testnet avec LNbits
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

def generate_lnd_config(output_path: str, testnet: bool = True):
    """Génère un fichier de configuration LND optimisé"""
    
    config = """# Configuration LND générée automatiquement
# Optimisée pour le testnet et LNbits

[Application Options]
# Activer le débogage
debuglevel=info

# Configuration du réseau
network=testnet
listen=0.0.0.0:9735

# Configuration des frais
bitcoind.estimatemode=ECONOMICAL
bitcoind.txfee=1000

[Bitcoin]
# Activer Bitcoin
bitcoin.active=1
bitcoin.testnet=1

# Configuration du nœud Bitcoin
bitcoind.rpcuser=bitcoinrpc
bitcoind.rpcpass=changeme
bitcoind.rpcport=18332
bitcoind.zmqpubrawblock=tcp://127.0.0.1:28332
bitcoind.zmqpubrawtx=tcp://127.0.0.1:28333

[Autopilot]
# Configuration de l'autopilote
autopilot.active=1
autopilot.maxchannels=5
autopilot.allocation=0.6
autopilot.minchansize=20000
autopilot.maxchansize=16777215
autopilot.private=0
autopilot.minconfs=1
autopilot.conftarget=3

[Routing]
# Configuration du routage
routing.assumechanvalid=1
routing.strictgraphpruning=1

[Channeldb]
# Configuration de la base de données des canaux
channeldb.no-mcp=1

[Neutrino]
# Configuration Neutrino pour le testnet
neutrino.connect=testnet.lightning.directory:18333
neutrino.maxpeers=8
neutrino.persistfilters=true
neutrino.validatechannels=false

[Tor]
# Configuration Tor (optionnelle)
tor.active=0
tor.socks=9050
tor.dns=nodes.lightning.directory:53

[Watchtower]
# Configuration des watchtowers
watchtower.active=1
watchtower.tower-dir=.watchtower
watchtower.external-ip=
watchtower.external-ip-port=9911

[Healthcheck]
# Configuration des healthchecks
healthcheck.active=1
healthcheck.ping-interval=1m
healthcheck.ping-timeout=5s
healthcheck.check-interval=1m

[Logging]
# Configuration des logs
log-level=info
log-file=.lnd/logs/lnd.log
log-max-backups=3
log-max-size=10MB
"""
    
    # Vérifier si le chemin est accessible en écriture
    try:
        # Créer le répertoire parent si nécessaire
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Tester l'écriture dans le répertoire
        test_file = os.path.join(output_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        # Écrire la configuration
        with open(output_path, 'w') as f:
            f.write(config)
        
        print(f"Configuration LND générée avec succès dans : {output_path}")
        print("\nInstructions :")
        print("1. Vérifiez et ajustez les paramètres selon vos besoins")
        print("2. Assurez-vous que le nœud Bitcoin est configuré correctement")
        print("3. Redémarrez LND pour appliquer la nouvelle configuration")
        
        return True
    
    except (PermissionError, OSError) as e:
        print(f"Erreur d'accès au système de fichiers : {str(e)}")
        print(f"Le chemin '{output_path}' n'est pas accessible en écriture.")
        
        # Proposer des chemins alternatifs
        home_dir = os.path.expanduser("~")
        temp_dir = tempfile.gettempdir()
        
        print("\nChemins alternatifs suggérés :")
        print(f"1. Dossier personnel : {os.path.join(home_dir, 'lnd.conf')}")
        print(f"2. Dossier temporaire : {os.path.join(temp_dir, 'lnd.conf')}")
        print(f"3. Dossier courant : {os.path.join(os.getcwd(), 'lnd.conf')}")
        
        return False

def main():
    parser = argparse.ArgumentParser(description="Générateur de configuration LND pour le testnet")
    parser.add_argument(
        "--output", 
        default="~/.lnd/lnd.conf",
        help="Chemin de sortie pour le fichier de configuration (défaut: ~/.lnd/lnd.conf)"
    )
    parser.add_argument(
        "--testnet",
        action="store_true",
        default=True,
        help="Générer une configuration pour le testnet (défaut: True)"
    )
    
    args = parser.parse_args()
    
    # Expansion du chemin utilisateur
    output_path = os.path.expanduser(args.output)
    
    try:
        success = generate_lnd_config(output_path, args.testnet)
        if not success:
            # Demander à l'utilisateur s'il souhaite utiliser un chemin alternatif
            choice = input("\nVoulez-vous utiliser un chemin alternatif ? (o/n) : ").strip().lower()
            if choice == 'o':
                alt_path = input("Entrez le chemin alternatif : ").strip()
                alt_path = os.path.expanduser(alt_path)
                success = generate_lnd_config(alt_path, args.testnet)
                if not success:
                    sys.exit(1)
            else:
                sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de la génération de la configuration : {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 