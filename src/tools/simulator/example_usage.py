#!/usr/bin/env python3
"""
Exemple d'utilisation du simulateur stochastique de nœuds Lightning.
Ce script démontre comment configurer et utiliser le simulateur pour tester un moteur de décision.

Dernière mise à jour: 7 mai 2025
"""

import logging
import json
from pathlib import Path
import numpy as np
from typing import Dict, Any, List
import random

from .stochastic_simulator import LightningSimEnvironment, DecisionEvaluator
from .scenario_matrix import ScenarioMatrix
from .simulation_fixtures import SimulationFixtures

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("example_usage")

class SimpleDecisionEngine:
    """
    Moteur de décision simple pour tester le simulateur.
    Implémente quelques heuristiques basiques.
    """
    
    def __init__(self):
        """Initialise le moteur de décision"""
        self.config = {
            "min_forwards_threshold": 10,     # Seuil minimum de forwards pour considérer un canal actif
            "success_rate_threshold": 0.8,    # Taux de succès minimum acceptable
            "fee_increase_threshold": 0.7,    # Seuil de capacité utilisée pour augmenter les frais
            "fee_decrease_threshold": 0.3,    # Seuil de capacité inutilisée pour baisser les frais
            "inactivity_threshold": 5,        # Seuil de forwards en dessous duquel un canal est considéré inactif
            "fee_adjustment_factor": 0.2      # Facteur d'ajustement des frais (±20%)
        }
    
    def evaluate_network(self, network_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Évalue l'état du réseau et prend des décisions sur les politiques de frais
        
        Args:
            network_state: État actuel du réseau
            
        Returns:
            Liste des décisions à appliquer
        """
        decisions = []
        
        # Extraire les canaux du réseau
        channels = network_state["network"]["channels"]
        
        for channel in channels:
            # Ne considérer que les canaux actifs
            if not channel.get("active", True):
                continue
                
            channel_id = channel.get("channel_id", "unknown")
            capacity = channel.get("capacity", 0)
            local_balance = channel.get("local_balance", 0)
            remote_balance = channel.get("remote_balance", 0)
            total_forwards = channel.get("total_forwards", 0)
            successful_forwards = channel.get("successful_forwards", 0)
            
            # Calculer quelques métriques dérivées
            success_rate = successful_forwards / max(1, total_forwards)
            local_ratio = local_balance / max(1, capacity)
            
            # Vérifier l'activité du canal
            is_active = total_forwards >= self.config["min_forwards_threshold"]
            
            # Heuristique 1: Canal inactif -> Baisser les frais
            if not is_active:
                decision = {
                    "channel_id": channel_id,
                    "action": "DECREASE_FEES",
                    "fee_base_change": -int(channel.get("local_fee_base_msat", 1000) * self.config["fee_adjustment_factor"] / 1000),
                    "fee_rate_change": -int(channel.get("local_fee_rate", 500) * self.config["fee_adjustment_factor"]),
                    "reason": "Canal inactif, baisse des frais pour attirer du trafic"
                }
                decisions.append(decision)
                continue
            
            # Heuristique 2: Taux de succès bas -> Ajuster la politique
            if success_rate < self.config["success_rate_threshold"]:
                # Si le problème semble être un manque de liquidité locale (outbound)
                if local_ratio < 0.2:
                    decision = {
                        "channel_id": channel_id,
                        "action": "INCREASE_FEES",
                        "fee_base_change": int(channel.get("local_fee_base_msat", 1000) * self.config["fee_adjustment_factor"] / 1000),
                        "fee_rate_change": int(channel.get("local_fee_rate", 500) * self.config["fee_adjustment_factor"]),
                        "reason": "Manque de liquidité locale, augmentation des frais pour préserver la liquidité"
                    }
                # Si le problème semble être un manque de liquidité distante (inbound)
                elif remote_ratio < 0.2:
                    decision = {
                        "channel_id": channel_id,
                        "action": "DECREASE_FEES",
                        "fee_base_change": -int(channel.get("local_fee_base_msat", 1000) * self.config["fee_adjustment_factor"] / 1000),
                        "fee_rate_change": -int(channel.get("local_fee_rate", 500) * self.config["fee_adjustment_factor"]),
                        "reason": "Manque de liquidité distante, baisse des frais pour attirer de la liquidité"
                    }
                else:
                    # Problème autre que la liquidité, considérer fermer le canal si vraiment problématique
                    if success_rate < 0.5:
                        decision = {
                            "channel_id": channel_id,
                            "action": "CLOSE_CHANNEL",
                            "reason": "Taux de succès critique, fermeture du canal recommandée"
                        }
                    else:
                        # Sinon, ne rien faire pour le moment
                        continue
                        
                decisions.append(decision)
                continue
            
            # Heuristique 3: Gestion de la liquidité par les frais
            if local_ratio > self.config["fee_increase_threshold"]:
                # Trop de liquidité locale, augmenter les frais pour encourager les sorties
                decision = {
                    "channel_id": channel_id,
                    "action": "INCREASE_FEES",
                    "fee_base_change": int(channel.get("local_fee_base_msat", 1000) * self.config["fee_adjustment_factor"] / 1000),
                    "fee_rate_change": int(channel.get("local_fee_rate", 500) * self.config["fee_adjustment_factor"]),
                    "reason": "Excès de liquidité locale, augmentation des frais pour encourager l'utilisation"
                }
                decisions.append(decision)
            elif local_ratio < self.config["fee_decrease_threshold"]:
                # Trop peu de liquidité locale, baisser les frais pour encourager les entrées
                decision = {
                    "channel_id": channel_id,
                    "action": "DECREASE_FEES",
                    "fee_base_change": -int(channel.get("local_fee_base_msat", 1000) * self.config["fee_adjustment_factor"] / 1000),
                    "fee_rate_change": -int(channel.get("local_fee_rate", 500) * self.config["fee_adjustment_factor"]),
                    "reason": "Manque de liquidité locale, baisse des frais pour limiter les sorties"
                }
                decisions.append(decision)
                
        return decisions


def run_simulation_demo():
    """
    Démontre l'utilisation du simulateur avec un moteur de décision simple
    """
    # 1. Créer une matrice de scénarios variés
    scenario_matrix = ScenarioMatrix()
    scenarios = scenario_matrix.generate_scenario_combinations(sample_size=5)
    
    # 2. Configurer l'environnement de simulation
    config = {
        "network_size": 20,            # 20 nœuds
        "scenarios": scenarios,        # Utiliser les scénarios générés
        "simulation_days": 30,         # Simuler sur 30 jours
        "noise_level": 0.2,            # 20% de bruit aléatoire
        "save_results": True           # Sauvegarder les résultats
    }
    
    # 3. Initialiser l'environnement de simulation
    simulator = LightningSimEnvironment(config)
    
    # 4. Créer un évaluateur pour le moteur de décision
    evaluator = DecisionEvaluator(simulator)
    
    # 5. Obtenir une référence sans intervention
    logger.info("Exécution de la simulation de référence...")
    baseline_results = evaluator.run_baseline_simulation(steps=30)
    
    # 6. Évaluer notre moteur de décision simple
    logger.info("Exécution de la simulation avec le moteur de décision simple...")
    decision_engine = SimpleDecisionEngine()
    evaluation = evaluator.evaluate_decision_engine(decision_engine, steps=30)
    
    # 7. Afficher les résultats comparatifs
    comparison = evaluation["comparison"]
    recommendations = evaluation["recommendations"]
    
    logger.info("=== Résultats de l'évaluation ===")
    logger.info(f"Score qualité: {comparison.get('decision_quality', 0):.2f}/10")
    logger.info(f"Amélioration des revenus: {comparison.get('revenue_ratio', 1.0):.2f}x")
    logger.info(f"Amélioration de l'efficacité du capital: {comparison.get('capital_efficiency_ratio', 1.0):.2f}x")
    logger.info(f"Amélioration du taux de succès: {comparison.get('htlc_success_rate_ratio', 1.0):.2f}x")
    
    logger.info("Recommandations:")
    for i, recommendation in enumerate(recommendations, 1):
        logger.info(f"{i}. {recommendation}")
    
    # 8. Exemple d'utilisation des fixtures pour générer des données historiques
    logger.info("Génération d'un scénario historique...")
    historical_scenario = SimulationFixtures.generate_historical_scenario(
        scenario_type="growth", days=60)
    
    # Sauvegarder la fixture pour utilisation future
    SimulationFixtures.save_fixture(
        historical_scenario, "exemple_growth_scenario")
    
    logger.info("Démonstration terminée. Les résultats sont disponibles dans le dossier data/stress_test/results/")


def run_extreme_traffic_scenarios():
    """
    Lance des scénarios de test extrêmes :
    - Nœud à fort trafic
    - Nœud à faible trafic
    - Nœud avec comportements aléatoires
    """
    scenario_matrix = ScenarioMatrix()
    # Scénario fort trafic
    high_traffic_scenario = {
        "node_centrality": 0.9,
        "volume_level": 5000,  # Trafic très élevé
        "liquidity_balance": 0.7,
        "fee_policy": "aggressive",
        "network_volatility": 0.2,
        "channel_age": 180,
        "channel_capacity": 15000000
    }
    # Scénario faible trafic
    low_traffic_scenario = {
        "node_centrality": 0.2,
        "volume_level": 2,  # Trafic très faible
        "liquidity_balance": 0.3,
        "fee_policy": "passive",
        "network_volatility": 0.1,
        "channel_age": 30,
        "channel_capacity": 1000000
    }
    # Scénario aléatoire/robustesse
    random_behavior_scenario = {
        "node_centrality": random.choice([0.1, 0.5, 0.9]),
        "volume_level": random.randint(1, 10000),
        "liquidity_balance": random.uniform(0.1, 0.9),
        "fee_policy": random.choice(["aggressive", "moderate", "passive"]),
        "network_volatility": random.uniform(0.1, 0.6),
        "channel_age": random.choice([7, 30, 180, 365]),
        "channel_capacity": random.choice([1000000, 5000000, 15000000])
    }
    scenarios = [high_traffic_scenario, low_traffic_scenario, random_behavior_scenario]

    config = {
        "network_size": 10,
        "scenarios": scenarios,
        "simulation_days": 20,
        "noise_level": 0.3,  # Plus de bruit pour tester la robustesse
        "save_results": True
    }
    simulator = LightningSimEnvironment(config)
    evaluator = DecisionEvaluator(simulator)
    logger.info("Simulation extrême : référence sans intervention...")
    baseline_results = evaluator.run_baseline_simulation(steps=20)
    logger.info("Simulation extrême : moteur de décision simple...")
    decision_engine = SimpleDecisionEngine()
    evaluation = evaluator.evaluate_decision_engine(decision_engine, steps=20)
    comparison = evaluation["comparison"]
    logger.info("=== Résultats scénarios extrêmes ===")
    logger.info(f"Score qualité: {comparison.get('decision_quality', 0):.2f}/10")
    logger.info(f"Amélioration des revenus: {comparison.get('revenue_ratio', 1.0):.2f}x")
    logger.info(f"Amélioration de l'efficacité du capital: {comparison.get('capital_efficiency_ratio', 1.0):.2f}x")
    logger.info(f"Amélioration du taux de succès: {comparison.get('htlc_success_rate_ratio', 1.0):.2f}x")
    logger.info("Démonstration extrême terminée. Les résultats sont disponibles dans le dossier data/stress_test/results/")


if __name__ == "__main__":
    # Exécuter la démonstration standard
    run_simulation_demo()
    # Exécuter les scénarios extrêmes
    run_extreme_traffic_scenarios() 