#!/usr/bin/env python3
# coding: utf-8
"""
Script d'optimisation automatique des nœuds Lightning.
Détecte les comportements anormaux et applique automatiquement des corrections.

Dernière mise à jour: 10 mai 2025
"""

import argparse
import logging
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import pymongo

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.append(str(Path(__file__).parent.parent))

# Importation des modules personnalisés
from tools.evaluate_simulations import calculate_node_score
from optimizers.performance_tracker import PerformanceTracker
from tools.auto_optimizer import NodeOptimizer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/optimizer.log")
    ]
)
logger = logging.getLogger("optimize_and_execute")

# Intervalle par défaut entre les vérifications (1 heure)
CHECK_INTERVAL = 3600

def parse_args():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Optimisation automatique des nœuds Lightning")
    parser.add_argument("--node-id", required=True, help="ID du nœud à optimiser")
    parser.add_argument("--dry-run", action="store_true", help="Mode simulation sans appliquer les changements")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Intervalle entre les vérifications (secondes)")
    parser.add_argument("--force", action="store_true", help="Forcer une optimisation immédiate")
    parser.add_argument("--config", type=str, default=".env", help="Fichier de configuration")
    parser.add_argument("--simulate", action="store_true", help="Utiliser des données simulées au lieu de données réelles")
    return parser.parse_args()

def load_env(config_file):
    """Charge les variables d'environnement à partir d'un fichier"""
    env_vars = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
                os.environ[key.strip()] = value.strip().strip('"\'')
        logger.info(f"Configuration chargée depuis {config_file}")
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
    return env_vars

def get_db_connection():
    """Établit une connexion à la base de données MongoDB"""
    try:
        from config import MONGO_URL, MONGO_DB_NAME
        client = pymongo.MongoClient(MONGO_URL)
        db = client[MONGO_DB_NAME]
        logger.info(f"Connexion à la base de données {MONGO_DB_NAME} établie")
        return db
    except Exception as e:
        logger.error(f"Erreur lors de la connexion à la base de données: {e}")
        raise

class LNbitsClientFactory:
    """Fabrique de clients LNbits"""
    
    def __init__(self, simulate=False):
        """
        Initialise la fabrique de clients
        
        Args:
            simulate: Si True, utilise un client simulé au lieu d'un client réel
        """
        self.simulate = simulate
        self.clients = {}
        
    def get_client(self, node_id):
        """
        Récupère ou crée un client pour un nœud donné
        
        Args:
            node_id: ID du nœud
            
        Returns:
            Client pour le nœud spécifié
        """
        if node_id not in self.clients:
            if self.simulate:
                logger.info(f"Création d'un client simulé pour le nœud {node_id}")
                self.clients[node_id] = SimulatedLNbitsClient(node_id)
            else:
                logger.info(f"Création d'un client LNbits pour le nœud {node_id}")
                api_key = os.environ.get("LNBITS_ADMIN_KEY", "")
                url = os.environ.get("LNBITS_URL", "http://localhost:5000")
                self.clients[node_id] = LNbitsClient(node_id, api_key, url)
                
        return self.clients[node_id]


class LNbitsClient:
    """Client pour interagir avec LNbits"""
    
    def __init__(self, node_id, api_key, url):
        """
        Initialise le client LNbits
        
        Args:
            node_id: ID du nœud
            api_key: Clé API LNbits
            url: URL de l'instance LNbits
        """
        self.node_id = node_id
        self.api_key = api_key
        self.url = url
        
    def get_node_data(self):
        """
        Récupère les données du nœud
        
        Returns:
            Dict contenant les données du nœud
        """
        logger.info(f"Récupération des données du nœud {self.node_id}")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, renvoyer des données simulées
        return {
            "node_id": self.node_id,
            "alias": f"Node {self.node_id[:8]}",
            "channels": self.get_channels(),
            "metrics": {
                "activity": {
                    "forwards_count": 150,
                    "success_rate": 0.85
                },
                "centrality": {
                    "betweenness": 0.5,
                    "closeness": 0.6
                }
            }
        }
        
    def get_channels(self):
        """
        Récupère la liste des canaux du nœud
        
        Returns:
            Liste des canaux
        """
        logger.info(f"Récupération des canaux du nœud {self.node_id}")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, renvoyer des données simulées
        return [
            {
                "channel_id": f"{self.node_id[:8]}_chan_1",
                "remote_pubkey": "remote_1",
                "local_balance": 800000,
                "remote_balance": 200000,
                "capacity": 1000000
            },
            {
                "channel_id": f"{self.node_id[:8]}_chan_2",
                "remote_pubkey": "remote_2",
                "local_balance": 500000,
                "remote_balance": 500000,
                "capacity": 1000000
            },
            {
                "channel_id": f"{self.node_id[:8]}_chan_3",
                "remote_pubkey": "remote_3",
                "local_balance": 300000,
                "remote_balance": 700000,
                "capacity": 1000000
            }
        ]
        
    def get_current_fees(self):
        """
        Récupère les frais actuels pour chaque canal
        
        Returns:
            Dict avec les frais par canal
        """
        logger.info(f"Récupération des frais du nœud {self.node_id}")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, renvoyer des données simulées
        channels = self.get_channels()
        fees = {}
        
        for channel in channels:
            fees[channel["channel_id"]] = {
                "base_fee": 1000,  # msats
                "fee_rate": 500    # ppm
            }
            
        return fees
        
    def update_channel_fees(self, new_fees):
        """
        Met à jour les frais des canaux
        
        Args:
            new_fees: Dict avec les nouveaux frais par canal
            
        Returns:
            Résultat de l'opération
        """
        logger.info(f"Mise à jour des frais pour {len(new_fees)} canaux")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, simuler une réponse
        return {
            "success": True,
            "updated": list(new_fees.keys())
        }
        
    def rebalance_channels(self, channels_to_rebalance):
        """
        Rééquilibre les canaux spécifiés
        
        Args:
            channels_to_rebalance: Liste des canaux à rééquilibrer
            
        Returns:
            Résultat de l'opération
        """
        logger.info(f"Rééquilibrage de {len(channels_to_rebalance)} canaux")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, simuler une réponse
        return {
            "success": True,
            "rebalanced": [c["channel_id"] for c in channels_to_rebalance]
        }
        
    def get_daily_revenue(self):
        """
        Récupère le revenu quotidien du nœud
        
        Returns:
            Revenu en sats
        """
        logger.info(f"Récupération du revenu quotidien du nœud {self.node_id}")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, renvoyer une valeur simulée
        return 5000  # sats
        
    def get_forward_success_rate(self):
        """
        Récupère le taux de succès des forwards
        
        Returns:
            Taux de succès (0-1)
        """
        logger.info(f"Récupération du taux de succès des forwards du nœud {self.node_id}")
        
        # TODO: Implémenter l'appel API réel à LNbits
        
        # Pour l'instant, renvoyer une valeur simulée
        return 0.85
        
    def get_liquidity_balance(self):
        """
        Calcule l'équilibre de liquidité global du nœud (0-1)
        Valeur idéale: 0.5 (50% local, 50% remote)
        
        Returns:
            Ratio de liquidité sortante
        """
        logger.info(f"Calcul de l'équilibre de liquidité du nœud {self.node_id}")
        
        channels = self.get_channels()
        total_local = sum(chan["local_balance"] for chan in channels)
        total_remote = sum(chan["remote_balance"] for chan in channels)
        total = total_local + total_remote
        
        if total == 0:
            return 0.5
            
        return total_local / total


class SimulatedLNbitsClient(LNbitsClient):
    """Client simulé pour les tests"""
    
    def __init__(self, node_id):
        """
        Initialise le client simulé
        
        Args:
            node_id: ID du nœud simulé
        """
        super().__init__(node_id, "fake_api_key", "http://localhost:5000")
        self.profile = self._select_random_profile()
        
    def _select_random_profile(self):
        """
        Sélectionne un profil aléatoire pour la simulation
        
        Returns:
            Nom du profil
        """
        # Vérifier si un profil est forcé via variable d'environnement
        forced_profile = os.environ.get("FORCE_PROFILE")
        if forced_profile:
            logger.info(f"Utilisation du profil forcé: {forced_profile}")
            return forced_profile
            
        import random
        profiles = [
            "normal", "saturated", "inactive", "abused", 
            "star", "unstable", "aggressive_fees", "routing_hub"
        ]
        return random.choice(profiles)
        
    def get_node_data(self):
        """
        Génère des données de nœud simulées
        
        Returns:
            Dict avec les données simulées
        """
        logger.info(f"Génération de données simulées pour le nœud {self.node_id} (profil: {self.profile})")
        
        # Charger des données simulées à partir des fichiers de simulation
        try:
            sim_file_pattern = f"rag/RAG_assets/nodes/simulations/feustey_sim_{self.profile}_*.json"
            sim_files = list(Path().glob(sim_file_pattern))
            
            if sim_files:
                latest_sim = max(sim_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"Utilisation du fichier de simulation {latest_sim}")
                
                with open(latest_sim, "r") as f:
                    sim_data = json.load(f)
                    
                # Adapter les données au format attendu
                sim_data["node_id"] = self.node_id
                return sim_data
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données simulées: {e}")
        
        # Fallback: génération de données simulées basiques
        return super().get_node_data()
        
    def update_channel_fees(self, new_fees):
        """
        Simule la mise à jour des frais
        
        Args:
            new_fees: Dict avec les nouveaux frais
            
        Returns:
            Résultat simulé
        """
        logger.info(f"Simulation de mise à jour des frais pour {len(new_fees)} canaux")
        
        # Simuler un taux de succès de 90%
        import random
        success = random.random() < 0.9
        
        if success:
            return {
                "success": True,
                "updated": list(new_fees.keys())
            }
        else:
            # Simuler un échec partiel
            updated = list(new_fees.keys())[:len(new_fees)//2]
            return {
                "success": False,
                "updated": updated,
                "error": "Certains canaux n'ont pas pu être mis à jour"
            }
            
    def rebalance_channels(self, channels_to_rebalance):
        """
        Simule le rééquilibrage des canaux
        
        Args:
            channels_to_rebalance: Liste des canaux à rééquilibrer
            
        Returns:
            Résultat simulé
        """
        logger.info(f"Simulation de rééquilibrage pour {len(channels_to_rebalance)} canaux")
        
        # Simuler un taux de succès de 75%
        import random
        success_rate = 0.75
        
        rebalanced = []
        for channel in channels_to_rebalance:
            if random.random() < success_rate:
                rebalanced.append(channel["channel_id"])
                
        return {
            "success": len(rebalanced) > 0,
            "rebalanced": rebalanced,
            "total": len(channels_to_rebalance)
        }
        
    def get_daily_revenue(self):
        """
        Simule le revenu quotidien
        
        Returns:
            Revenu simulé en sats
        """
        if self.profile == "star":
            return 10000
        elif self.profile == "routing_hub":
            return 20000
        elif self.profile == "dead_node":
            return 50
        elif self.profile == "inactive":
            return 500
        else:
            return 5000
            
    def get_forward_success_rate(self):
        """
        Simule le taux de succès des forwards
        
        Returns:
            Taux de succès simulé
        """
        if self.profile == "star":
            return 0.98
        elif self.profile == "abused":
            return 0.65
        elif self.profile == "unstable":
            return 0.75
        elif self.profile == "experimental":
            return 0.50
        else:
            return 0.85
            
    def get_liquidity_balance(self):
        """
        Simule l'équilibre de liquidité
        
        Returns:
            Ratio de liquidité simulé
        """
        if self.profile == "saturated":
            return 0.9  # Déséquilibre, trop de liquidité sortante
        elif self.profile == "abused":
            return 0.2  # Déséquilibre, trop peu de liquidité sortante
        else:
            return 0.5  # Équilibré


def main():
    """Fonction principale d'exécution"""
    args = parse_args()
    
    # Créer le répertoire de logs s'il n'existe pas
    Path("logs").mkdir(exist_ok=True)
    
    # Charger la configuration
    load_env(args.config)
    
    try:
        # Initialiser les composants
        client_factory = LNbitsClientFactory(simulate=args.simulate)
        db_connection = get_db_connection()
        optimizer = NodeOptimizer(client_factory)
        tracker = PerformanceTracker(db_connection)
        
        logger.info(f"Démarrage de l'optimisation pour le nœud {args.node_id}")
        if args.dry_run:
            logger.info("Mode DRY RUN activé - aucune modification ne sera appliquée")
        
        # Boucle principale d'optimisation
        while True:
            try:
                # 1. Récupérer l'état actuel du nœud
                client = client_factory.get_client(args.node_id)
                node_data = client.get_node_data()
                initial_state = {
                    "revenue": client.get_daily_revenue(),
                    "success_rate": client.get_forward_success_rate(),
                    "liquidity_balance": client.get_liquidity_balance()
                }
                
                logger.info(f"État actuel du nœud: {initial_state}")
                
                # 2. Évaluer le nœud
                evaluation = calculate_node_score(node_data)
                logger.info(f"Évaluation du nœud: score={evaluation['overall_score']}, "
                           f"recommandation={evaluation['recommendation']}")
                
                # 3. Vérifier si une action est nécessaire
                if ("CRITIQUE" in evaluation["recommendation"] or 
                    "ATTENTION" in evaluation["recommendation"] or 
                    args.force):
                    # Appliquer les optimisations
                    logger.info(f"Optimisation nécessaire: {evaluation['recommendation']}")
                    
                    # 4. Appliquer les recommandations
                    actions = optimizer.apply_recommendations(
                        args.node_id, evaluation, dry_run=args.dry_run
                    )
                    
                    if actions and not args.dry_run:
                        logger.info(f"Actions appliquées: {actions}")
                        
                        # 5. Attendre un peu pour voir l'effet des actions
                        wait_time = 600  # 10 minutes
                        logger.info(f"Attente de {wait_time}s pour mesurer l'impact...")
                        time.sleep(wait_time)
                        
                        # 6. Mesurer l'impact
                        final_state = {
                            "revenue": client.get_daily_revenue(),
                            "success_rate": client.get_forward_success_rate(),
                            "liquidity_balance": client.get_liquidity_balance()
                        }
                        
                        logger.info(f"État final du nœud: {final_state}")
                        
                        # 7. Enregistrer pour apprentissage
                        result = tracker.record_performance(
                            args.node_id, actions, initial_state, final_state
                        )
                        logger.info(f"Impact des actions: {result}")
                        
                    elif args.dry_run:
                        logger.info(f"Actions proposées (dry-run): {actions}")
                else:
                    logger.info("Aucune action nécessaire pour le moment")
                
                # Si c'est un run forcé unique, sortir
                if args.force:
                    break
                    
                # Attendre jusqu'à la prochaine vérification
                logger.info(f"Prochaine vérification dans {args.interval} secondes")
                time.sleep(args.interval)
                
            except Exception as e:
                logger.error(f"Erreur lors de l'optimisation: {e}")
                time.sleep(300)  # Attendre 5 minutes en cas d'erreur
                
    except KeyboardInterrupt:
        logger.info("Arrêt de l'optimisation")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 