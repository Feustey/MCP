#!/usr/bin/env python3
import os
import sys
import asyncio
import json
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Ajouter le répertoire parent au chemin Python pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integrations.data_aggregator import ExternalDataAggregator
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/external_data_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

async def load_node_list(node_list_file: str) -> List[str]:
    """
    Charge la liste des nœuds à surveiller depuis un fichier JSON.
    
    Args:
        node_list_file: Chemin vers le fichier contenant la liste des nœuds
        
    Returns:
        List[str]: Liste des clés publiques des nœuds
    """
    try:
        if os.path.exists(node_list_file):
            with open(node_list_file, 'r') as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "nodes" in data:
                    return data["nodes"]
                else:
                    logger.warning(f"Format de fichier non reconnu: {node_list_file}")
                    return []
        else:
            logger.warning(f"Fichier de liste de nœuds non trouvé: {node_list_file}")
            return []
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la liste des nœuds: {str(e)}")
        return []

async def add_default_nodes(nodes: List[str]) -> List[str]:
    """
    Ajoute des nœuds par défaut à surveiller si la liste est vide.
    
    Args:
        nodes: Liste actuelle des nœuds
        
    Returns:
        List[str]: Liste des nœuds complétée avec les nœuds par défaut
    """
    if not nodes:
        # Ajouter quelques nœuds de référence du réseau Lightning
        default_nodes = [
            "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",  # ACINQ
            "02d96eadea3d780104449aca5c93461ce67c1564e2e1d73225fa67dd3b997a919b",  # Bitfinex
            "034ea80f8b148c750463546bd999bf7321a0e6dfc60aaf84bd0400a2e8d376c0f9",  # River Financial
            "02d4531a2f2e6e5a9033d37d548cff4834a3898e74c3abe1985b493c42ebbd707d",  # Kraken
            "03c2abfa93eacec04721c019644584424aab2ba4dff3ac9bdab4e9c97007491dda",  # Bottlepay
            "0279c22ed7a068d10dc1a38ae66d2d6461e269226c60258c021b1ddcdfe4b00bc4"   # Lightning Labs
        ]
        logger.info(f"Utilisation des nœuds par défaut: {len(default_nodes)} nœuds ajoutés")
        return default_nodes
    return nodes

async def main():
    """Fonction principale pour l'exécution des mises à jour périodiques."""
    parser = argparse.ArgumentParser(description='Gestion des mises à jour des données externes')
    parser.add_argument('--node-list', type=str, default='data/nodes_to_track.json',
                        help='Fichier JSON contenant la liste des nœuds à surveiller')
    parser.add_argument('--interval', type=int, default=3600,
                        help='Intervalle entre les mises à jour (en secondes)')
    parser.add_argument('--run-once', action='store_true',
                        help='Exécuter une seule mise à jour puis s\'arrêter')
    
    args = parser.parse_args()
    
    # Création du répertoire de logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)
    
    # Chargement de la liste des nœuds
    nodes = await load_node_list(args.node_list)
    nodes = await add_default_nodes(nodes)
    
    logger.info(f"Démarrage du processus de mise à jour des données pour {len(nodes)} nœuds")
    
    # Initialisation et exécution de l'agrégateur
    aggregator = ExternalDataAggregator()
    
    # Définir l'intervalle de mise à jour
    aggregator.update_interval = args.interval
    
    # Initialiser les connexions
    if await aggregator.initialize():
        try:
            # Exécution des mises à jour
            await aggregator.run_periodic_update(nodes, args.run_once)
        except KeyboardInterrupt:
            logger.info("Interruption manuelle du processus")
        finally:
            # Fermer proprement les connexions
            await aggregator.close()
    else:
        logger.error("Échec de l'initialisation des connexions, arrêt du processus")

if __name__ == "__main__":
    asyncio.run(main()) 