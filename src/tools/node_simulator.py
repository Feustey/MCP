#!/usr/bin/env python3
"""
Simulateur de nœud Lightning pour MCP.
Ce module permet de simuler différents comportements de nœuds: saturé, inactif, abusé, star, etc.
Il utilise les données réelles du nœud feustey pour générer des simulations réalistes.

Dernière mise à jour: 9 mai 2025
"""

import json
import random
import copy
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("node_simulator")

# Chemin vers les données réelles du nœud feustey
FEUSTEY_DATA_PATH = Path("rag/RAG_assets/nodes/feustey/raw_data")
SIMULATOR_OUTPUT_PATH = Path("rag/RAG_assets/nodes/simulations")

# Pubkey du nœud feustey
FEUSTEY_PUBKEY = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

# Profils de comportement de nœuds
NODE_BEHAVIORS = {
    "normal": {
        "success_rate": 0.95,
        "forwards_count_daily": 150,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 1000,
            "fee_rate": 500
        },
        "fee_behavior": "stable"
    },
    "saturated": {
        "success_rate": 0.7,
        "forwards_count_daily": 300,
        "liquidity_balance": 0.85,  # Déséquilibre en faveur du local
        "fee_policy": {
            "base_fee": 1500,
            "fee_rate": 700
        },
        "fee_behavior": "stable"
    },
    "inactive": {
        "success_rate": 0.9,
        "forwards_count_daily": 20,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 1000,
            "fee_rate": 500
        },
        "fee_behavior": "stable"
    },
    "abused": {
        "success_rate": 0.6,
        "forwards_count_daily": 250,
        "liquidity_balance": 0.2,  # Déséquilibre en faveur du remote
        "fee_policy": {
            "base_fee": 500,
            "fee_rate": 200
        },
        "fee_behavior": "stable",
        "anomalies": {
            "unbalanced_channels": True
        }
    },
    "star": {
        "success_rate": 0.98,
        "forwards_count_daily": 500,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 1000,
            "fee_rate": 500
        },
        "fee_behavior": "stable",
        "connection_count": 150  # Grand nombre de connexions
    },
    "unstable": {
        "success_rate": 0.85,
        "forwards_count_daily": 100,
        "liquidity_balance": 0.6,
        "fee_policy": {
            "base_fee": 1200,
            "fee_rate": 600
        },
        "fee_behavior": "volatile",
        "uptime": 0.7,
        "anomalies": {
            "connection_instability": 0.3,  # 30% d'instabilité
            "random_failures": True
        }
    },
    "aggressive_fees": {
        "success_rate": 0.8,
        "forwards_count_daily": 120,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 3000,
            "fee_rate": 1500
        },
        "fee_behavior": "aggressive",
        "anomalies": {
            "high_failure_low_liquidity": True
        }
    },
    "routing_hub": {
        "success_rate": 0.96,
        "forwards_count_daily": 1000,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 800,
            "fee_rate": 400
        },
        "fee_behavior": "optimized",
        "connection_count": 200  # Très grand nombre de connexions
    },
    "dead_node": {
        "success_rate": 0.2,
        "forwards_count_daily": 5,
        "liquidity_balance": 0.5,
        "fee_policy": {
            "base_fee": 1000,
            "fee_rate": 500
        },
        "fee_behavior": "unchanged",
        "anomalies": {
            "offline_periods": True,
            "stagnant_activity": True
        }
    },
    "experimental": {
        "success_rate": random.uniform(0.3, 0.9),
        "forwards_count_daily": int(random.uniform(10, 500)),
        "liquidity_balance": random.uniform(0.1, 0.9),
        "fee_policy": {
            "base_fee": int(random.uniform(100, 10000)),
            "fee_rate": int(random.uniform(10, 1000))
        },
        "fee_behavior": "highly_volatile",
        "data_anomalies": True   # Peut contenir des données incohérentes ou manquantes
    }
}

class NodeSimulator:
    """Simulateur de nœud Lightning"""
    
    def __init__(self):
        """Initialisation du simulateur avec les données de référence"""
        self.base_node_data = None
        self.load_reference_data()
        
        # Créer le répertoire de sortie s'il n'existe pas
        SIMULATOR_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    def load_reference_data(self):
        """Charge les données réelles du nœud feustey"""
        try:
            # Récupérer le fichier le plus récent
            data_files = list(FEUSTEY_DATA_PATH.glob("*.json"))
            if not data_files:
                raise FileNotFoundError("Aucun fichier de données trouvé pour feustey")
            
            latest_file = max(data_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Chargement des données depuis {latest_file}")
            
            with open(latest_file, "r") as f:
                self.base_node_data = json.load(f)
                
            logger.info(f"Données chargées: {len(self.base_node_data['channels'])} canaux")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}")
            raise
    
    def _update_channels_for_behavior(self, channels, behavior_profile):
        """Ajuste les canaux selon le profil de comportement"""
        behavior = NODE_BEHAVIORS[behavior_profile]
        updated_channels = []
        
        for channel in channels:
            # Créer une copie pour ne pas modifier l'original
            new_channel = copy.deepcopy(channel)
            
            # Récupérer les données de base
            capacity = channel.get("capacity", 5000000)
            
            # Ajuster l'équilibre en fonction du profil
            local_ratio = behavior["liquidity_balance"]
            new_channel["local_balance"] = int(capacity * local_ratio)
            new_channel["remote_balance"] = int(capacity * (1.0 - local_ratio))
            
            # Ajuster les frais en fonction du profil
            base_fee = behavior["fee_policy"]["base_fee"]
            fee_rate = behavior["fee_policy"]["fee_rate"]
            
            # Ajouter une variation pour plus de réalisme
            variation = random.uniform(0.8, 1.2)
            
            new_channel["local_fee_rate"] = int(fee_rate * variation)
            
            # Ajouter des anomalies si applicable
            if behavior_profile == "unstable":
                # Canal parfois inactif
                new_channel["active"] = random.random() > behavior.get("anomalies", {}).get("connection_instability", 0)
                
            elif behavior_profile == "saturated":
                # Capacité proche d'être totalement utilisée
                new_channel["remote_balance"] = int(capacity * 0.05)  # Seulement 5% de liquidité entrante
                
            elif behavior_profile == "abused":
                # Local balance très faible
                remote_ratio = 0.8 + random.uniform(0, 0.15)  # 80-95% distant
                new_channel["local_balance"] = int(capacity * (1.0 - remote_ratio))
                new_channel["remote_balance"] = int(capacity * remote_ratio)
                
            elif behavior_profile == "dead_node":
                # Canal inactif
                new_channel["active"] = random.random() > 0.8  # 80% de chance d'être inactif
                
            updated_channels.append(new_channel)
            
        return updated_channels
    
    def _update_metrics_for_behavior(self, behavior_profile):
        """Génère des métriques en fonction du profil de comportement"""
        behavior = NODE_BEHAVIORS[behavior_profile]
        
        # Ajuster les métriques de centralité
        centrality_base = {
            "saturated": {"betweenness": 0.7, "closeness": 0.5, "eigenvector": 0.6},
            "inactive": {"betweenness": 0.2, "closeness": 0.3, "eigenvector": 0.15},
            "abused": {"betweenness": 0.4, "closeness": 0.3, "eigenvector": 0.2},
            "normal": {"betweenness": 0.45, "closeness": 0.5, "eigenvector": 0.4},
            "star": {"betweenness": 0.85, "closeness": 0.75, "eigenvector": 0.9},
            "unstable": {"betweenness": 0.5, "closeness": 0.45, "eigenvector": 0.3},
            "aggressive_fees": {"betweenness": 0.4, "closeness": 0.4, "eigenvector": 0.35},
            "routing_hub": {"betweenness": 0.95, "closeness": 0.9, "eigenvector": 0.95},
            "dead_node": {"betweenness": 0.05, "closeness": 0.1, "eigenvector": 0.05},
            "experimental": {"betweenness": random.uniform(0.1, 0.9), 
                            "closeness": random.uniform(0.1, 0.9),
                            "eigenvector": random.uniform(0.1, 0.9)},
        }
        
        # Ajouter une variation aléatoire
        centrality = {
            k: min(1.0, max(0.1, v * random.uniform(0.9, 1.1)))
            for k, v in centrality_base[behavior_profile].items()
        }
        
        # Générer des métriques d'activité
        activity = {
            "forwards_count": int(behavior["forwards_count_daily"] * random.uniform(0.9, 1.1)),
            "success_rate": min(1.0, behavior["success_rate"] * random.uniform(0.95, 1.05)),
            "avg_fee_earned": int(behavior["fee_policy"]["fee_rate"] * 0.4)
        }
        
        # Ajouter des métriques supplémentaires pour les nouveaux profils
        additional_metrics = {}
        
        if behavior_profile == "unstable":
            additional_metrics["uptime"] = behavior.get("uptime", 0.9) * random.uniform(0.95, 1.05)
            additional_metrics["connection_stability"] = 1.0 - behavior.get("anomalies", {}).get("connection_instability", 0)
            additional_metrics["random_failures"] = True if behavior.get("anomalies", {}).get("random_failures") else False
            
        elif behavior_profile == "routing_hub":
            additional_metrics["network_centrality"] = random.uniform(0.85, 0.98)
            additional_metrics["connection_count"] = behavior.get("connection_count", 100)
            additional_metrics["liquidity_utilization"] = random.uniform(0.7, 0.9)
            
        elif behavior_profile == "dead_node":
            additional_metrics["dormancy_period"] = "90+ days"
            additional_metrics["response_time"] = "timeout"
            
        elif behavior_profile == "experimental":
            # Métriques aléatoires et potentiellement incohérentes
            if random.random() < 0.3:
                additional_metrics["error_rate"] = random.uniform(0.05, 0.5)
            if random.random() < 0.4:
                additional_metrics["data_quality"] = random.uniform(0.3, 0.9)
            if random.random() < 0.2:
                additional_metrics["anomaly_score"] = random.uniform(0.6, 1.0)
        
        return {
            "centrality": centrality,
            "activity": activity,
            "additional": additional_metrics
        }
    
    def _update_fees_data(self, behavior_profile):
        """Génère des données de frais pour le profil de comportement"""
        behavior = NODE_BEHAVIORS[behavior_profile]
        
        # Base pour les frais entrants/sortants
        in_fee = behavior["fee_policy"]["fee_rate"] * 1.2  # Frais légèrement plus élevés pour le trafic entrant
        out_fee = behavior["fee_policy"]["fee_rate"]
        
        # Distribution des frais par heure (simulation de trafic)
        hours = list(range(24))
        
        # Générer des distributions différentes selon les profils
        if behavior_profile == "saturated":
            traffic_pattern = [random.uniform(0.5, 1.0) for _ in range(24)]
        elif behavior_profile == "inactive":
            traffic_pattern = [random.uniform(0.0, 0.3) for _ in range(24)]
        elif behavior_profile == "abused":
            traffic_pattern = [random.uniform(0.7, 1.0) if i in range(8, 18) else random.uniform(0.1, 0.3) for i in range(24)]
        elif behavior_profile == "star":
            traffic_pattern = [random.uniform(0.7, 1.0) for _ in range(24)]
        elif behavior_profile == "unstable":
            # Périodes d'activité suivies de périodes d'inactivité
            traffic_pattern = [random.uniform(0.7, 1.0) if random.random() < 0.7 else random.uniform(0.0, 0.2) for _ in range(24)]
        elif behavior_profile == "aggressive_fees":
            # Trafic modéré mais avec frais élevés
            traffic_pattern = [random.uniform(0.3, 0.6) for _ in range(24)]
            in_fee *= 1.5  # Augmentation supplémentaire des frais entrants
        elif behavior_profile == "routing_hub":
            # Trafic élevé à toute heure
            traffic_pattern = [random.uniform(0.7, 1.0) for _ in range(24)]
            # Léger cycle quotidien avec pic aux heures de bureau
            for i in range(9, 18):
                traffic_pattern[i] = min(1.0, traffic_pattern[i] * 1.2)
        elif behavior_profile == "dead_node":
            # Quasiment aucun trafic
            traffic_pattern = [random.uniform(0.0, 0.1) for _ in range(24)]
        elif behavior_profile == "experimental":
            # Pattern complètement aléatoire
            traffic_pattern = [random.uniform(0.0, 1.0) for _ in range(24)]
            # Possibilité de valeurs aberrantes
            if random.random() < 0.2:
                for i in random.sample(range(24), 3):  # 3 heures avec valeurs aberrantes
                    traffic_pattern[i] = random.uniform(0.8, 3.0)  # Potentiellement au-delà des valeurs normales
        else:  # normal
            traffic_pattern = [random.uniform(0.3, 0.8) for _ in range(24)]
        
        # Calculer les frais horaires
        in_fees = {str(h): int(in_fee * traffic_pattern[h] * behavior["forwards_count_daily"] / 24) for h in hours}
        out_fees = {str(h): int(out_fee * traffic_pattern[h] * behavior["forwards_count_daily"] / 24) for h in hours}
        
        # Calculer le total des frais
        cumul_fees = sum(in_fees.values()) + sum(out_fees.values())
        
        # Ajouter des anomalies pour les comportements spéciaux
        if behavior_profile == "experimental" and random.random() < 0.3:
            # Ajouter des valeurs manquantes
            for h in random.sample(hours, int(len(hours) * 0.2)):
                if random.random() < 0.5:
                    in_fees[str(h)] = None
                else:
                    out_fees[str(h)] = None
            
        return {
            "in": in_fees,
            "out": out_fees
        }, cumul_fees
    
    def generate_simulation(self, behavior_profile="normal"):
        """Génère une simulation de nœud avec le profil de comportement spécifié"""
        if behavior_profile not in NODE_BEHAVIORS:
            raise ValueError(f"Profil de comportement inconnu: {behavior_profile}")
        
        if not self.base_node_data:
            raise ValueError("Données de base non chargées")
        
        # Créer une copie des données de base
        simulated_data = copy.deepcopy(self.base_node_data)
        
        # Mettre à jour l'horodatage
        simulated_data["timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Mettre à jour les canaux
        simulated_data["channels"] = self._update_channels_for_behavior(
            simulated_data["channels"], 
            behavior_profile
        )
        
        # Mettre à jour les métriques
        simulated_data["metrics"] = self._update_metrics_for_behavior(behavior_profile)
        
        # Mettre à jour les données de frais
        simulated_data["fees"], simulated_data["cumul_fees"] = self._update_fees_data(behavior_profile)
        
        # Ajouter des attributs de simulation
        simulated_data["simulation_info"] = {
            "profile": behavior_profile,
            "generated_at": datetime.now().isoformat(),
            "base_data_source": str(FEUSTEY_DATA_PATH)
        }
        
        return simulated_data
    
    def save_simulation(self, simulated_data, prefix="feustey_sim"):
        """Sauvegarde la simulation dans un fichier JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile = simulated_data["simulation_info"]["profile"]
        
        filename = f"{prefix}_{profile}_{timestamp}.json"
        filepath = SIMULATOR_OUTPUT_PATH / filename
        
        with open(filepath, "w") as f:
            json.dump(simulated_data, f, indent=2)
        
        logger.info(f"Simulation sauvegardée dans {filepath}")
        return filepath

# Tests and demo functions
async def test_node_behaviors():
    """Teste la génération de simulations pour différents comportements"""
    simulator = NodeSimulator()
    
    # Tester tous les comportements définis
    for profile in NODE_BEHAVIORS.keys():
        logger.info(f"Génération d'une simulation pour le profil '{profile}'")
        
        # Générer la simulation
        sim_data = simulator.generate_simulation(profile)
        
        # Sauvegarder la simulation
        filepath = simulator.save_simulation(sim_data)
        
        # Afficher quelques statistiques
        metrics = sim_data["metrics"]["activity"]
        logger.info(f"  - Forwards: {metrics['forwards_count']}")
        logger.info(f"  - Taux de succès: {metrics['success_rate']:.2f}")
        logger.info(f"  - Frais cumulés: {sim_data['cumul_fees']}")
        logger.info(f"  - Sauvegardé dans: {filepath}")

async def main():
    """Fonction principale"""
    try:
        simulator = NodeSimulator()
        
        # Générer des simulations pour tous les profils
        for profile in NODE_BEHAVIORS.keys():
            logger.info(f"Génération d'une simulation pour le profil '{profile}'")
            sim_data = simulator.generate_simulation(profile)
            
            # Enregistrer la simulation
            file_path = simulator.save_simulation(sim_data)
            
            # Afficher quelques statistiques
            forwards = sim_data.get("metrics", {}).get("activity", {}).get("forwards_count", 0)
            success_rate = sim_data.get("metrics", {}).get("activity", {}).get("success_rate", 0)
            fees = sim_data.get("cumul_fees", 0)
            
            logger.info(f"- Forwards: {forwards}")
            logger.info(f"  - Taux de succès: {success_rate:.2f}")
            logger.info(f"  - Frais cumulés: {fees}")
            logger.info(f"  - Sauvegardé dans: {file_path}")
        
        # Exécuter l'évaluation des simulations
        logger.info("Lancement de l'évaluation comparative des simulations...")
        import sys
        import os
        
        # Ajouter le répertoire courant au chemin de recherche des modules
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Importer le module d'évaluation
        from evaluate_simulations import main as evaluate_main
        evaluate_main()
        logger.info("Évaluation comparative terminée.")
        
    except Exception as e:
        logger.error(f"Erreur lors de la simulation: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())