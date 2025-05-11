#!/usr/bin/env python3
"""
Simulateur de nœud Lightning pour MCP

Ce module simule différents comportements de nœuds Lightning
pour tester les fonctionnalités du système MCP sans nécessiter
un nœud Lightning réel.

Dernière mise à jour: 25 juin 2025
"""

import os
import sys
import json
import time
import uuid
import random
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Ajouter le répertoire parent au sys.path pour les imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(parent_dir)

from src.models import NodeData, ChannelData

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/node_simulator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("node_simulator")

# Constantes et configurations
DEFAULT_SIMULATION_PATH = "data/simulation"
NODE_TYPES = ["hub", "regional", "service", "routing", "unstable"]
CHANNEL_TYPES = ["major_hub", "regional_node", "specialized_service", "volume_channel"]

class NodeSimulator:
    """Classe principale pour simuler un nœud Lightning et ses canaux"""
    
    def __init__(self, scenario: str = "standard"):
        """
        Initialise le simulateur de nœud
        
        Args:
            scenario: Type de scénario à simuler (standard, degraded, optimal)
        """
        self.scenario = scenario
        self.simulation_path = os.environ.get("SIMULATION_PATH", DEFAULT_SIMULATION_PATH)
        self.nodes: Dict[str, Dict] = {}
        self.channels: Dict[str, Dict] = {}
        self.timestamp = datetime.datetime.now().isoformat()
        
        # Charger la configuration du scénario
        self._load_scenario()
        
        # Créer le répertoire de simulation s'il n'existe pas
        Path(self.simulation_path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Simulateur initialisé avec le scénario: {scenario}")
        
    def _load_scenario(self):
        """Charger la configuration du scénario"""
        if self.scenario == "standard":
            self.node_count = 15
            self.channel_count = 30
            self.success_rate_range = (0.5, 0.95)
            self.forward_count_range = (10, 500)
            self.capacity_range = (500000, 5000000)  # en sats
            self.degradation_factor = 0.0
        elif self.scenario == "degraded":
            self.node_count = 10
            self.channel_count = 20
            self.success_rate_range = (0.3, 0.8)
            self.forward_count_range = (5, 300)
            self.capacity_range = (500000, 3000000)
            self.degradation_factor = 0.3
        elif self.scenario == "optimal":
            self.node_count = 20
            self.channel_count = 40
            self.success_rate_range = (0.7, 0.99)
            self.forward_count_range = (50, 800)
            self.capacity_range = (1000000, 10000000)
            self.degradation_factor = -0.1
        else:
            # Scénario personnalisé ou par défaut
            self.node_count = int(os.environ.get("SIMULATION_NODE_COUNT", 15))
            self.channel_count = int(os.environ.get("SIMULATION_CHANNEL_COUNT", 30))
            self.success_rate_range = (0.5, 0.95)
            self.forward_count_range = (10, 500)
            self.capacity_range = (500000, 5000000)
            self.degradation_factor = float(os.environ.get("SIMULATION_DEGRADATION", 0.0))
    
    def generate_nodes(self) -> List[Dict]:
        """
        Génère un ensemble de nœuds simulés
        
        Returns:
            Liste de nœuds simulés
        """
        logger.info(f"Génération de {self.node_count} nœuds...")
        
        for i in range(self.node_count):
            node_type = random.choice(NODE_TYPES)
            node_id = f"{uuid.uuid4().hex[:8]}{'0' * 58}"
            
            # Caractéristiques différentes selon le type
            if node_type == "hub":
                centrality = random.uniform(0.8, 0.95)
                channel_count = random.randint(50, 200)
                alias = f"Hub_{i+1}"
            elif node_type == "regional":
                centrality = random.uniform(0.4, 0.8)
                channel_count = random.randint(20, 60)
                alias = f"Regional_{i+1}" 
            elif node_type == "service":
                centrality = random.uniform(0.3, 0.6)
                channel_count = random.randint(5, 20)
                alias = f"Service_{i+1}"
            elif node_type == "routing":
                centrality = random.uniform(0.5, 0.7)
                channel_count = random.randint(10, 40)
                alias = f"Router_{i+1}"
            elif node_type == "unstable":
                centrality = random.uniform(0.1, 0.4)
                channel_count = random.randint(2, 15)
                alias = f"Unstable_{i+1}"
            
            # Créer le nœud
            node = {
                "node_id": node_id,
                "pubkey": node_id,
                "alias": alias,
                "color": f"#{random.randint(0, 0xFFFFFF):06x}",
                "type": node_type,
                "last_update": self.timestamp,
                "capacity": {
                    "total": 0,  # Sera mis à jour après la génération des canaux
                    "channels": channel_count
                },
                "scores": {
                    "availability": random.uniform(0.7, 0.99),
                    "centrality": centrality,
                    "stability": random.uniform(0.5, 0.95),
                    "fee_efficiency": random.uniform(0.3, 0.9),
                    "overall": 0.0  # Sera calculé plus tard
                },
                "channels": []
            }
            
            # Calculer le score global
            node["scores"]["overall"] = (
                node["scores"]["availability"] * 0.25 +
                node["scores"]["centrality"] * 0.25 +
                node["scores"]["stability"] * 0.25 +
                node["scores"]["fee_efficiency"] * 0.25
            )
            
            self.nodes[node_id] = node
        
        logger.info(f"{len(self.nodes)} nœuds générés")
        return list(self.nodes.values())
    
    def generate_channels(self) -> List[Dict]:
        """
        Génère un ensemble de canaux entre les nœuds simulés
        
        Returns:
            Liste de canaux simulés
        """
        logger.info(f"Génération de {self.channel_count} canaux...")
        
        node_ids = list(self.nodes.keys())
        for i in range(self.channel_count):
            # Sélectionner deux nœuds différents
            node1_id = random.choice(node_ids)
            node2_id = random.choice([n for n in node_ids if n != node1_id])
            
            # Créer un ID de canal unique
            channel_id = f"{uuid.uuid4().hex[:8]}:{uuid.uuid4().hex[:8]}"
            short_channel_id = f"{random.randint(600000, 800000)}:{random.randint(0, 5000)}:{random.randint(0, 3)}"
            
            # Déterminer le type de canal
            node1_type = self.nodes[node1_id]["type"]
            node2_type = self.nodes[node2_id]["type"]
            
            if node1_type == "hub" or node2_type == "hub":
                channel_type = "major_hub"
                capacity = random.randint(3000000, 10000000)
            elif node1_type == "regional" or node2_type == "regional":
                channel_type = "regional_node"
                capacity = random.randint(1000000, 5000000)
            elif node1_type == "service" or node2_type == "service":
                channel_type = "specialized_service"
                capacity = random.randint(500000, 3000000)
            else:
                channel_type = "volume_channel"
                capacity = random.randint(200000, 2000000)
            
            # Simuler un déséquilibre de liquidité
            local_ratio = random.uniform(0.1, 0.9)
            local_balance = int(capacity * local_ratio)
            remote_balance = capacity - local_balance
            
            # Politiques spécifiques selon le type
            if channel_type == "major_hub":
                fee_base_1 = random.randint(800, 1500)
                fee_rate_1 = random.randint(150, 250)
                fee_base_2 = random.randint(500, 1200)
                fee_rate_2 = random.randint(50, 150)
            elif channel_type == "regional_node":
                fee_base_1 = random.randint(600, 1200)
                fee_rate_1 = random.randint(100, 200)
                fee_base_2 = random.randint(500, 1000)
                fee_rate_2 = random.randint(40, 120)
            elif channel_type == "specialized_service":
                fee_base_1 = random.randint(400, 1000)
                fee_rate_1 = random.randint(80, 180)
                fee_base_2 = random.randint(300, 800)
                fee_rate_2 = random.randint(30, 100)
            else:  # volume_channel
                fee_base_1 = random.randint(300, 800)
                fee_rate_1 = random.randint(50, 150)
                fee_base_2 = random.randint(200, 600)
                fee_rate_2 = random.randint(20, 80)
            
            # Créer le canal
            channel = {
                "channel_id": channel_id,
                "short_channel_id": short_channel_id,
                "transaction_id": uuid.uuid4().hex,
                "transaction_vout": random.randint(0, 3),
                "capacity": capacity,
                "node1_pub": node1_id,
                "node2_pub": node2_id,
                "node1_alias": self.nodes[node1_id]["alias"],
                "node2_alias": self.nodes[node2_id]["alias"],
                "created_at": (datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 365))).isoformat(),
                "last_update": self.timestamp,
                "status": "active",
                "type": channel_type,
                "balance": {
                    "local": local_balance,
                    "remote": remote_balance,
                    "ratio": local_ratio
                },
                "policies": {
                    "node1": {
                        "fee_base_msat": fee_base_1,
                        "fee_rate_milli_msat": fee_rate_1,
                        "min_htlc_msat": 1000,
                        "max_htlc_msat": capacity * 1000,
                        "time_lock_delta": 40,
                        "disabled": False
                    },
                    "node2": {
                        "fee_base_msat": fee_base_2,
                        "fee_rate_milli_msat": fee_rate_2,
                        "min_htlc_msat": 1000,
                        "max_htlc_msat": capacity * 1000,
                        "time_lock_delta": 40,
                        "disabled": False
                    }
                }
            }
            
            # Générer des métriques de performance pour le canal
            success_rate = random.uniform(*self.success_rate_range)
            if self.degradation_factor > 0:
                success_rate *= (1 - self.degradation_factor)
            
            forwards_count = random.randint(*self.forward_count_range)
            if self.degradation_factor > 0:
                forwards_count = int(forwards_count * (1 - self.degradation_factor))
            
            avg_htlc = random.randint(10000, 500000)
            revenue_msat = int(forwards_count * avg_htlc * fee_rate_1 / 1000000)
            
            channel["metrics"] = {
                "forwards_count": forwards_count,
                "forwards_volume_sat": forwards_count * avg_htlc / 1000,
                "success_rate": round(success_rate, 3),
                "average_htlc_size": avg_htlc,
                "revenue_msat": revenue_msat,
                "uptime": random.uniform(0.8, 0.99)
            }
            
            # Ajouter le canal
            self.channels[channel_id] = channel
            
            # Mettre à jour la capacité des nœuds
            self.nodes[node1_id]["capacity"]["total"] += capacity
            self.nodes[node2_id]["capacity"]["total"] += capacity
            
            # Ajouter la référence au canal dans les nœuds
            self.nodes[node1_id]["channels"].append(channel_id)
            self.nodes[node2_id]["channels"].append(channel_id)
            
        logger.info(f"{len(self.channels)} canaux générés")
        return list(self.channels.values())
    
    def generate_simulation_data(self):
        """Génère et sauvegarde l'ensemble des données de simulation"""
        logger.info("Démarrage de la génération de données de simulation...")
        
        # Générer les nœuds et canaux
        self.generate_nodes()
        self.generate_channels()
        
        # Créer un dossier pour cette simulation
        simulation_id = f"{self.scenario}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        simulation_dir = os.path.join(self.simulation_path, simulation_id)
        Path(simulation_dir).mkdir(parents=True, exist_ok=True)
        
        # Enregistrer les nœuds et canaux générés
        with open(os.path.join(simulation_dir, "nodes.json"), "w") as f:
            json.dump(list(self.nodes.values()), f, indent=2)
        
        with open(os.path.join(simulation_dir, "channels.json"), "w") as f:
            json.dump(list(self.channels.values()), f, indent=2)
        
        # Enregistrer les métadonnées de la simulation
        metadata = {
            "simulation_id": simulation_id,
            "scenario": self.scenario,
            "timestamp": self.timestamp,
            "node_count": self.node_count,
            "channel_count": self.channel_count,
            "success_rate_range": self.success_rate_range,
            "forward_count_range": self.forward_count_range,
            "capacity_range": self.capacity_range,
            "degradation_factor": self.degradation_factor
        }
        
        with open(os.path.join(simulation_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Données de simulation générées dans: {simulation_dir}")
        
        # Créer un lien symbolique vers la dernière simulation
        latest_link = os.path.join(self.simulation_path, "latest")
        if os.path.islink(latest_link):
            os.unlink(latest_link)
        
        try:
            os.symlink(simulation_dir, latest_link)
            logger.info(f"Lien symbolique 'latest' mis à jour: {latest_link} -> {simulation_dir}")
        except Exception as e:
            logger.warning(f"Impossible de créer le lien symbolique: {e}")
        
        return simulation_dir
    
    def run_simulation(self, duration_seconds: int = 300, update_interval: int = 10):
        """
        Exécute une simulation en temps réel
        
        Args:
            duration_seconds: Durée de la simulation en secondes
            update_interval: Intervalle de mise à jour en secondes
        """
        logger.info(f"Démarrage de la simulation pour {duration_seconds} secondes...")
        
        # Générer les données initiales
        simulation_dir = self.generate_simulation_data()
        
        # Simuler l'exécution en temps réel
        start_time = time.time()
        end_time = start_time + duration_seconds
        update_count = 0
        
        while time.time() < end_time:
            # Attendre l'intervalle de mise à jour
            time.sleep(update_interval)
            update_count += 1
            
            # Mettre à jour les données
            self._update_simulation_data()
            
            # Enregistrer l'état mis à jour
            update_dir = os.path.join(simulation_dir, f"update_{update_count}")
            Path(update_dir).mkdir(parents=True, exist_ok=True)
            
            with open(os.path.join(update_dir, "nodes.json"), "w") as f:
                json.dump(list(self.nodes.values()), f, indent=2)
            
            with open(os.path.join(update_dir, "channels.json"), "w") as f:
                json.dump(list(self.channels.values()), f, indent=2)
            
            logger.info(f"Simulation mise à jour {update_count}: {update_interval}s écoulées, {int(end_time - time.time())}s restantes")
        
        logger.info("Simulation terminée")
        return simulation_dir
    
    def _update_simulation_data(self):
        """Met à jour les données de simulation pour simuler l'activité"""
        self.timestamp = datetime.datetime.now().isoformat()
        
        # Mettre à jour chaque canal
        for channel_id, channel in self.channels.items():
            # Simuler des fluctuations dans les métriques
            channel["metrics"]["forwards_count"] += random.randint(0, 10)
            channel["metrics"]["forwards_volume_sat"] += random.randint(0, 50000)
            
            # Simuler des changements de success_rate
            success_change = random.uniform(-0.05, 0.05)
            new_success_rate = max(0.1, min(0.99, channel["metrics"]["success_rate"] + success_change))
            channel["metrics"]["success_rate"] = round(new_success_rate, 3)
            
            # Simuler des changements de balance
            balance_change = random.uniform(-0.1, 0.1)
            new_ratio = max(0.05, min(0.95, channel["balance"]["ratio"] + balance_change))
            channel["balance"]["ratio"] = new_ratio
            channel["balance"]["local"] = int(channel["capacity"] * new_ratio)
            channel["balance"]["remote"] = channel["capacity"] - channel["balance"]["local"]
            
            # Mettre à jour la date de dernière modification
            channel["last_update"] = self.timestamp
        
        # Mettre à jour les scores des nœuds
        for node_id, node in self.nodes.items():
            # Simuler des fluctuations dans les scores
            for score_key in ["availability", "stability", "fee_efficiency"]:
                score_change = random.uniform(-0.05, 0.05)
                new_score = max(0.1, min(0.99, node["scores"][score_key] + score_change))
                node["scores"][score_key] = round(new_score, 3)
            
            # Recalculer le score global
            node["scores"]["overall"] = (
                node["scores"]["availability"] * 0.25 +
                node["scores"]["centrality"] * 0.25 +
                node["scores"]["stability"] * 0.25 +
                node["scores"]["fee_efficiency"] * 0.25
            )
            
            # Mettre à jour la date
            node["last_update"] = self.timestamp

def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulateur de nœud Lightning pour MCP")
    parser.add_argument("--scenario", type=str, default="standard", 
                      choices=["standard", "degraded", "optimal", "custom"],
                      help="Scénario de simulation à utiliser")
    parser.add_argument("--duration", type=int, default=300,
                      help="Durée de la simulation en secondes")
    parser.add_argument("--interval", type=int, default=10,
                      help="Intervalle entre les mises à jour en secondes")
    parser.add_argument("--static", action="store_true",
                      help="Générer uniquement les données statiques sans simulation en temps réel")
    
    args = parser.parse_args()
    
    # Utiliser la valeur d'environnement si présente
    scenario = os.environ.get("SIMULATION_SCENARIO", args.scenario)
    
    # Initialiser le simulateur
    simulator = NodeSimulator(scenario=scenario)
    
    if args.static:
        # Générer uniquement les données statiques
        simulation_dir = simulator.generate_simulation_data()
        logger.info(f"Données statiques générées dans: {simulation_dir}")
    else:
        # Exécuter la simulation en temps réel
        simulation_dir = simulator.run_simulation(
            duration_seconds=args.duration,
            update_interval=args.interval
        )
        logger.info(f"Simulation exécutée dans: {simulation_dir}")

if __name__ == "__main__":
    main() 