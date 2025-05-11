#!/usr/bin/env python3
"""
Environnement de simulation stochastique pour nœuds Lightning.
Ce module intègre les métriques, l'évolution des canaux et les scénarios combinatoires.

Dernière mise à jour: 7 mai 2025
"""

import logging
import random
import numpy as np
import json
from typing import Dict, Any, List, Tuple, Optional, Callable, Union
from pathlib import Path
from datetime import datetime, timedelta

from .performance_metrics import PerformanceMetrics
from .channel_evolution import StochasticChannelEvolution
from .scenario_matrix import ScenarioMatrix
from .simulation_fixtures import SimulationFixtures

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stochastic_simulator")

# Chemin pour stocker les résultats
RESULTS_PATH = Path("data/stress_test/results")

class DummyDecisionEngine:
    """
    Moteur de décision factice qui ne fait rien.
    Utilisé pour établir une référence de comparaison.
    """
    
    def evaluate_network(self, network_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ne prend aucune décision
        
        Args:
            network_state: État actuel du réseau
            
        Returns:
            Liste vide de décisions
        """
        return []

class LightningSimEnvironment:
    """
    Environnement de simulation intégré pour évaluer les moteurs de décision
    dans différents scénarios stochastiques.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'environnement de simulation
        
        Args:
            config: Configuration de l'environnement
                - network_size: Taille du réseau
                - scenarios: Liste de scénarios à simuler
                - simulation_days: Nombre de jours à simuler
                - noise_level: Niveau de bruit
                - save_results: Sauvegarde des résultats
        """
        self.config = config
        self.metrics_tracker = PerformanceMetrics()
        self.network = self._build_network_from_config(config)
        self.time_step = 0
        self.history = []
        self.channel_evolutions = {}  # Stocke les objets d'évolution pour chaque canal
        
        logger.info(f"Environnement de simulation initialisé avec {len(self.network['channels'])} canaux")
        
        # Créer le répertoire de résultats si nécessaire
        if config.get("save_results", False):
            RESULTS_PATH.mkdir(parents=True, exist_ok=True)
    
    def _build_network_from_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construit un réseau Lightning basé sur la configuration
        
        Args:
            config: Configuration du réseau
            
        Returns:
            Dictionnaire représentant le réseau
        """
        network_size = config.get("network_size", 50)
        num_channels = network_size * 3  # Par défaut, en moyenne 6 canaux par nœud
        
        # Utiliser un scénario de base ou le premier scénario fourni
        if "scenarios" in config and len(config["scenarios"]) > 0:
            base_scenario = config["scenarios"][0]
        else:
            # Scénario par défaut modéré
            base_scenario = {
                "node_centrality": 0.5,
                "volume_level": 100,
                "liquidity_balance": 0.5,
                "fee_policy": "moderate",
                "network_volatility": 0.2
            }
        
        # Générer la topologie du réseau
        matrix = ScenarioMatrix()
        network = matrix.generate_network_topology(network_size, num_channels, base_scenario)
        
        # Si des scénarios sont fournis, les utiliser pour varier les paramètres des canaux
        if "scenarios" in config and len(config["scenarios"]) > 1:
            scenarios = config["scenarios"]
            # Remplacer certains canaux par des canaux générés à partir d'autres scénarios
            channels_per_scenario = max(1, len(network["channels"]) // (len(scenarios) - 1))
            
            for i, scenario in enumerate(scenarios[1:]):  # Skip le premier scénario déjà utilisé
                start_idx = i * channels_per_scenario
                end_idx = min((i + 1) * channels_per_scenario, len(network["channels"]))
                
                for j in range(start_idx, end_idx):
                    # Remplacer le canal par un nouveau généré à partir du scénario
                    channel = matrix.generate_channel_parameters(scenario)
                    # Conserver les indices de nœuds connectés
                    channel["node1_index"] = network["channels"][j]["node1_index"]
                    channel["node2_index"] = network["channels"][j]["node2_index"]
                    network["channels"][j] = channel
        
        return network
    
    def initialize_evolution_engines(self) -> None:
        """
        Initialise les moteurs d'évolution stochastique pour chaque canal
        """
        self.channel_evolutions = {}
        
        for channel in self.network["channels"]:
            # Déterminer les facteurs de volatilité en fonction du canal
            volatility_factors = {
                "volume": 0.1 + 0.2 * (1 - channel.get("centrality_score", 0.5)),  # Les nœuds périphériques ont plus de volatilité
                "success_rate": 0.05 + 0.1 * channel.get("network_volatility", 0.2),
                "liquidity": 0.2,
                "noise": 0.05 + 0.1 * channel.get("network_volatility", 0.2)
            }
            
            # Créer un moteur d'évolution pour ce canal
            channel_id = channel.get("channel_id", "unknown")
            self.channel_evolutions[channel_id] = StochasticChannelEvolution(
                channel, volatility_factors)
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Obtient l'état actuel du réseau et des métriques
        
        Returns:
            État actuel du système
        """
        # Collecter l'état actuel de tous les canaux
        current_channels = []
        for channel_id, evolution in self.channel_evolutions.items():
            current_channels.append(evolution.get_current_state())
        
        # Mettre à jour le réseau
        current_network = self.network.copy()
        current_network["channels"] = current_channels
        
        # Collecter les métriques actuelles
        current_metrics = self.metrics_tracker.get_metrics_snapshot()
        
        return {
            "network": current_network,
            "metrics": current_metrics,
            "time_step": self.time_step,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def apply_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        """
        Applique les décisions du moteur de décision aux canaux
        
        Args:
            decisions: Liste des décisions à appliquer
        """
        for decision in decisions:
            channel_id = decision.get("channel_id")
            
            if not channel_id or channel_id not in self.channel_evolutions:
                logger.warning(f"Décision pour un canal inconnu: {channel_id}")
                continue
                
            # Extraire les changements de politique
            action = decision.get("action", "NO_ACTION")
            
            if action == "NO_ACTION":
                continue
                
            # Préparer les changements de politique
            policy_changes = {}
            
            if action == "INCREASE_FEES":
                # Extraire les montants d'augmentation
                fee_base_change = decision.get("fee_base_change", 0)
                fee_rate_change = decision.get("fee_rate_change", 0)
                
                # Si aucun montant spécifique, utiliser des valeurs par défaut
                if fee_base_change == 0 and fee_rate_change == 0:
                    fee_base_change = 100  # +100 sats
                    fee_rate_change = 50   # +50 ppm
                    
                policy_changes = {
                    "fee_base_change": fee_base_change,
                    "fee_rate_change": fee_rate_change
                }
                
            elif action == "DECREASE_FEES":
                # Extraire les montants de diminution
                fee_base_change = decision.get("fee_base_change", 0)
                fee_rate_change = decision.get("fee_rate_change", 0)
                
                # Si aucun montant spécifique, utiliser des valeurs par défaut
                if fee_base_change == 0 and fee_rate_change == 0:
                    fee_base_change = -50   # -50 sats
                    fee_rate_change = -25   # -25 ppm
                    
                policy_changes = {
                    "fee_base_change": fee_base_change,
                    "fee_rate_change": fee_rate_change
                }
                
            elif action == "CLOSE_CHANNEL":
                # Pour l'instant, on simule une fermeture en réduisant fortement l'activité
                policy_changes = {
                    "channel_closed": True
                }
                # Cette information sera utilisée dans le prochain pas de simulation
                
            # Appliquer les changements à l'évolution du canal
            self.channel_evolutions[channel_id].simulate_step(0, policy_changes)
            
            logger.info(f"Décision appliquée pour canal {channel_id}: {action}")
    
    def evolve_network(self, time_delta: int = 1) -> None:
        """
        Fait évoluer naturellement le réseau sur une période donnée
        
        Args:
            time_delta: Nombre de jours à simuler
        """
        # Faire évoluer chaque canal
        for channel_id, evolution in self.channel_evolutions.items():
            evolution.simulate_step(time_delta)
        
        # Mettre à jour le timestamp
        self.time_step += time_delta
        
        # Calculer les métriques globales à partir des états des canaux
        self._update_global_metrics()
    
    def _update_global_metrics(self) -> None:
        """
        Met à jour les métriques globales basées sur l'état actuel du réseau
        """
        # Collecter l'état de tous les canaux
        all_channels = [evolution.get_current_state() 
                         for evolution in self.channel_evolutions.values()]
        
        # Calculer les métriques
        total_revenue = sum(channel.get("revenue", 0) for channel in all_channels)
        total_forwards = sum(channel.get("total_forwards", 0) for channel in all_channels)
        successful_forwards = sum(channel.get("successful_forwards", 0) for channel in all_channels)
        
        # Taux de succès global
        htlc_success_rate = successful_forwards / max(1, total_forwards)
        
        # Efficacité du capital
        total_capacity = sum(channel.get("capacity", 0) for channel in all_channels)
        capital_efficiency = successful_forwards / max(1, total_capacity / 100000)
        
        # Coût des rebalancements (dans un vrai système, cela viendrait de données réelles)
        # Pour la simulation, on estime un coût proportionnel aux déséquilibres
        rebalancing_cost = sum(
            abs(channel.get("local_balance", 0) - channel.get("capacity", 0) / 2) * 0.0001
            for channel in all_channels
        )
        
        # Compétitivité des frais (moyenne pondérée par succès)
        weighted_fee_rates = [
            channel.get("local_fee_rate", 0) * channel.get("successful_forwards", 0)
            for channel in all_channels
        ]
        avg_fee_rate = sum(weighted_fee_rates) / max(1, successful_forwards)
        
        # Normaliser la compétitivité (plus bas = plus compétitif, mais pas trop bas)
        # Une échelle de 0 à 1 où 0.5 est optimal
        fee_competitiveness = 1.0 / (1.0 + np.exp(-(avg_fee_rate - 500) / 200))
        
        # Rétention des pairs (canaux actifs / total)
        peer_retention_rate = sum(1 for channel in all_channels if channel.get("active", True)) / max(1, len(all_channels))
        
        # Mettre à jour les métriques globales
        updated_metrics = {
            "revenue": total_revenue,
            "opportunity_cost": total_forwards - successful_forwards,
            "capital_efficiency": capital_efficiency,
            "rebalancing_cost": rebalancing_cost,
            "peer_retention_rate": peer_retention_rate,
            "htlc_success_rate": htlc_success_rate,
            "fee_competitiveness": fee_competitiveness,
            "uptime": peer_retention_rate  # Simplification, en réalité plus complexe
        }
        
        self.metrics_tracker.update_metrics(updated_metrics)
        
        # Ajouter l'état actuel à l'historique
        self.history.append({
            "time_step": self.time_step,
            "metrics": updated_metrics.copy(),
            "channel_states": [channel.copy() for channel in all_channels]
        })
    
    def run_simulation(self, steps: int, decision_engine: Any) -> Dict[str, Any]:
        """
        Exécute la simulation sur plusieurs pas de temps
        en appliquant le moteur de décision à chaque étape
        
        Args:
            steps: Nombre de jours à simuler
            decision_engine: Moteur de décision à évaluer
            
        Returns:
            Résultats de la simulation
        """
        # Initialiser les moteurs d'évolution
        self.initialize_evolution_engines()
        
        # Réinitialiser l'historique et les métriques
        self.history = []
        self.metrics_tracker.reset()
        self.time_step = 0
        
        # Calculer les métriques initiales
        self._update_global_metrics()
        
        # Journalisation
        logger.info(f"Démarrage de la simulation sur {steps} jours")
        
        # Boucle principale de simulation
        for step in range(steps):
            # 1. Capturer l'état actuel
            current_state = self.get_current_state()
            
            # 2. Obtenir les décisions du moteur
            try:
                decisions = decision_engine.evaluate_network(current_state)
            except Exception as e:
                logger.error(f"Erreur lors de l'évaluation du réseau: {e}")
                decisions = []
            
            # 3. Appliquer les décisions
            self.apply_decisions(decisions)
            
            # 4. Simuler l'évolution naturelle du réseau
            self.evolve_network(time_delta=1)  # 1 jour
            
            # 5. Journalisation périodique
            if step % 5 == 0 or step == steps - 1:
                logger.info(f"Simulation jour {step+1}/{steps}")
        
        # Calculer les métriques de performance finale
        final_metrics = self.metrics_tracker.get_metrics_snapshot()
        
        # Calculer le taux d'amélioration
        improvement_rate = self._calculate_improvement_rate()
        
        # Assembler les résultats
        results = {
            'final_state': self.get_current_state(),
            'final_metrics': final_metrics,
            'improvement_rate': improvement_rate,
            'history': self.history,
            'config': self.config
        }
        
        # Sauvegarder les résultats si demandé
        if self.config.get("save_results", False):
            self._save_simulation_results(results)
        
        return results
    
    def _calculate_improvement_rate(self) -> Dict[str, float]:
        """
        Calcule le taux d'amélioration des métriques sur la durée de la simulation
        
        Returns:
            Dictionnaire des taux d'amélioration
        """
        if len(self.history) < 2:
            return {
                "revenue": 0.0,
                "efficiency": 0.0,
                "overall": 0.0
            }
        
        # Prendre les métriques initiales et finales
        initial = self.history[0]["metrics"]
        final = self.history[-1]["metrics"]
        
        # Calculer les taux d'amélioration relatifs
        improvement = {}
        
        for key in final.keys():
            if key in initial and initial[key] > 0:
                improvement[key] = (final[key] - initial[key]) / initial[key]
            else:
                improvement[key] = 0.0 if final[key] == 0 else 1.0
        
        # Calculer un score global pondéré
        weights = {
            "revenue": 0.25,
            "capital_efficiency": 0.20,
            "htlc_success_rate": 0.15,
            "fee_competitiveness": 0.15,
            "peer_retention_rate": 0.10,
            "opportunity_cost": -0.10,  # Négatif car on veut minimiser
            "rebalancing_cost": -0.05   # Négatif car on veut minimiser
        }
        
        overall = 0.0
        total_weight = 0.0
        
        for key, weight in weights.items():
            if key in improvement:
                # Pour les métriques à minimiser (poids négatif), inverser le signe
                value = improvement[key]
                if weight < 0:
                    value = -value
                    weight = -weight
                
                overall += value * weight
                total_weight += weight
        
        if total_weight > 0:
            overall = overall / total_weight
        
        return {
            "revenue": improvement.get("revenue", 0.0),
            "efficiency": improvement.get("capital_efficiency", 0.0),
            "success_rate": improvement.get("htlc_success_rate", 0.0),
            "opportunity_cost": improvement.get("opportunity_cost", 0.0),
            "overall": overall
        }
    
    def _save_simulation_results(self, results: Dict[str, Any]) -> None:
        """
        Sauvegarde les résultats de la simulation
        
        Args:
            results: Résultats à sauvegarder
        """
        try:
            # Créer le répertoire si nécessaire
            RESULTS_PATH.mkdir(parents=True, exist_ok=True)
            
            # Nom de fichier avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sim_results_{timestamp}.json"
            filepath = RESULTS_PATH / filename
            
            # Supprimer les objets non sérialisables
            results_copy = results.copy()
            
            # Simplifier l'historique pour la sauvegarde
            simplified_history = []
            for entry in results_copy["history"]:
                simplified_entry = {
                    "time_step": entry["time_step"],
                    "metrics": entry["metrics"]
                }
                simplified_history.append(simplified_entry)
            
            results_copy["history"] = simplified_history
            
            with open(filepath, "w") as f:
                json.dump(results_copy, f, indent=2)
                
            logger.info(f"Résultats sauvegardés dans {filepath}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des résultats: {e}")


class DecisionEvaluator:
    """
    Évaluateur pour tester et comparer les performances des moteurs de décision
    """
    
    def __init__(self, simulator: LightningSimEnvironment):
        """
        Initialise l'évaluateur avec un simulateur
        
        Args:
            simulator: Environnement de simulation à utiliser
        """
        self.simulator = simulator
        self.baseline_results = None
    
    def run_baseline_simulation(self, steps: int) -> Dict[str, Any]:
        """
        Exécute une simulation sans intervention pour établir une référence
        
        Args:
            steps: Nombre de jours à simuler
            
        Returns:
            Résultats de la simulation de référence
        """
        dummy_engine = DummyDecisionEngine()  # Moteur qui ne fait rien
        self.baseline_results = self.simulator.run_simulation(steps, dummy_engine)
        
        logger.info("Simulation de référence terminée")
        
        return self.baseline_results
    
    def evaluate_decision_engine(self, decision_engine: Any, steps: int) -> Dict[str, Any]:
        """
        Évalue les performances du moteur de décision par rapport à la référence
        
        Args:
            decision_engine: Moteur de décision à évaluer
            steps: Nombre de jours à simuler
            
        Returns:
            Résultats de l'évaluation
        """
        # Exécuter la simulation avec le moteur de décision
        results = self.simulator.run_simulation(steps, decision_engine)
        
        # Si aucune référence n'existe, en créer une
        if not self.baseline_results:
            logger.info("Aucune référence trouvée, génération de la baseline...")
            self.run_baseline_simulation(steps)
        
        # Comparer avec la référence
        comparison = self._compare_results(results, self.baseline_results)
        
        # Générer des recommandations
        recommendations = self._generate_improvement_recommendations(comparison, results["history"])
        
        return {
            'results': results,
            'baseline': self.baseline_results,
            'comparison': comparison,
            'recommendations': recommendations
        }
    
    def _compare_results(self, test_results: Dict[str, Any], 
                        baseline_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Compare les résultats de deux simulations
        
        Args:
            test_results: Résultats de la simulation à évaluer
            baseline_results: Résultats de la simulation de référence
            
        Returns:
            Comparaison des métriques clés
        """
        test_final = test_results["final_metrics"]
        baseline_final = baseline_results["final_metrics"]
        
        # Comparer les métriques finales
        comparison = {}
        
        for key in test_final.keys():
            if key in baseline_final and baseline_final[key] > 0:
                # Ratio d'amélioration
                comparison[f"{key}_ratio"] = test_final[key] / baseline_final[key]
                # Différence absolue
                comparison[f"{key}_diff"] = test_final[key] - baseline_final[key]
            else:
                comparison[f"{key}_ratio"] = 1.0
                comparison[f"{key}_diff"] = 0.0
        
        # Comparer les taux d'amélioration
        test_improvement = test_results["improvement_rate"]
        baseline_improvement = baseline_results["improvement_rate"]
        
        for key in test_improvement.keys():
            if key in baseline_improvement:
                # Différence des taux d'amélioration
                comparison[f"improvement_{key}_diff"] = test_improvement[key] - baseline_improvement[key]
        
        # Calculer un score global
        comparison["overall_score"] = (
            comparison.get("revenue_ratio", 1.0) * 0.3 +
            comparison.get("capital_efficiency_ratio", 1.0) * 0.2 +
            comparison.get("htlc_success_rate_ratio", 1.0) * 0.2 +
            (2 - comparison.get("opportunity_cost_ratio", 1.0)) * 0.15 +  # Inversé car on veut minimiser
            (2 - comparison.get("rebalancing_cost_ratio", 1.0)) * 0.15    # Inversé car on veut minimiser
        )
        
        # Normaliser sur une échelle de 0 à 10
        comparison["decision_quality"] = min(10, max(0, (comparison["overall_score"] - 0.8) * 50))
        
        return comparison
    
    def _generate_improvement_recommendations(self, comparison: Dict[str, float], 
                                           history: List[Dict[str, Any]]) -> List[str]:
        """
        Génère des recommandations pour améliorer le moteur de décision
        
        Args:
            comparison: Comparaison avec la référence
            history: Historique de la simulation
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # Analyser les forces et faiblesses
        if comparison.get("revenue_ratio", 1.0) < 1.05:
            recommendations.append(
                "Ajuster la politique d'augmentation des frais pour améliorer les revenus")
                
        if comparison.get("htlc_success_rate_ratio", 1.0) < 1.0:
            recommendations.append(
                "Revoir les critères de fermeture de canaux pour maintenir un meilleur taux de succès")
                
        if comparison.get("opportunity_cost_ratio", 1.0) > 1.0:
            recommendations.append(
                "Réduire les frais sur les canaux inactifs pour diminuer les coûts d'opportunité")
                
        if comparison.get("rebalancing_cost_ratio", 1.0) > 1.2:
            recommendations.append(
                "Optimiser les changements de frais pour réduire les besoins de rebalancement")
                
        if comparison.get("capital_efficiency_ratio", 1.0) < 1.0:
            recommendations.append(
                "Favoriser les canaux à fort volume pour améliorer l'efficacité du capital")
        
        # Recommandations générales si peu de problèmes spécifiques
        if len(recommendations) < 2:
            if comparison.get("decision_quality", 5) > 7:
                recommendations.append(
                    "Le moteur performe bien, envisager des stratégies plus agressives ou des contextes plus variés")
            else:
                recommendations.append(
                    "Diversifier les heuristiques de décision pour mieux répondre aux différents types de canaux")
                recommendations.append(
                    "Affiner la sensibilité aux métriques de performance pour équilibrer revenus et stabilité")
        
        return recommendations 