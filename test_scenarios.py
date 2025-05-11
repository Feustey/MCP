from typing import Dict, Any, Optional, List
import asyncio
import uuid
from datetime import datetime, timedelta
import json
import logging
import csv
import os
import math
import statistics
from pathlib import Path
from collections import defaultdict

from lnbits_client import LNBitsClient
from app.services.network_topology import NetworkTopologyAnalyzer
from app.services.performance_dashboard import PerformanceDashboard

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """
    Analyse les performances des différentes stratégies au fil du temps.
    Permet de répondre à des questions critiques comme:
    - Combien de cycles consécutifs notre heuristique bat-elle le hasard?
    - Quel est le facteur multiplicatif moyen de sats forwardés?
    """
    
    def __init__(self, data_dir: str = "collected_data"):
        self.data_dir = Path(data_dir)
        self.metrics_file = self.data_dir / "metrics_comparison.csv"
        self.performance_log = self.data_dir / "performance_stats.json"
        
        # Initialiser les analyseurs
        self.topology_analyzer = NetworkTopologyAnalyzer()
        self.dashboard = PerformanceDashboard(data_dir)
        
        # Statistiques sur les performances
        self.stats = {
            "cycles": [],
            "heuristic_streaks": [],
            "current_streak": 0,
            "multipliers": [],
            "volatility": {},
            "topological_effects": {}
        }
        
        # Charger les statistiques existantes si disponibles
        if self.performance_log.exists():
            try:
                with open(self.performance_log, "r") as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.error(f"Erreur lors du chargement des stats de performance: {e}")
        
        logger.info(f"PerformanceTracker initialisé avec {len(self.stats.get('cycles', []))} cycles analysés")
    
    def track_cycle(self, cycle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enregistre un nouveau cycle d'A/B testing complet.
        
        Args:
            cycle_data: Données du cycle (gagnant, performances, etc.)
            
        Returns:
            Statistiques mises à jour
        """
        # Ajouter le cycle aux données historiques
        self.stats["cycles"].append(cycle_data)
        
        # Analyser les séquences de victoires
        if cycle_data.get("winner") == "heuristic":
            self.stats["current_streak"] += 1
            
            # Calculer le multiplicateur par rapport au random
            if "heuristic_delta" in cycle_data and "random_delta" in cycle_data and cycle_data["random_delta"] > 0:
                multiplier = cycle_data["heuristic_delta"] / cycle_data["random_delta"]
                self.stats["multipliers"].append(multiplier)
        else:
            # Fin d'une série de victoires - enregistrer sa longueur
            if self.stats["current_streak"] > 0:
                self.stats["heuristic_streaks"].append(self.stats["current_streak"])
            self.stats["current_streak"] = 0
        
        # Calculer la volatilité pour chaque stratégie
        for strategy in ["heuristic", "random", "baseline"]:
            if f"{strategy}_delta" in cycle_data:
                if strategy not in self.stats["volatility"]:
                    self.stats["volatility"][strategy] = []
                
                self.stats["volatility"][strategy].append(cycle_data[f"{strategy}_delta"])
        
        # Analyser les effets topologiques si des données de canaux sont disponibles
        if "channels" in cycle_data:
            self.topology_analyzer.build_network_graph(cycle_data["channels"])
            node_id = cycle_data.get("node_id")
            if node_id:
                topo_features = self.topology_analyzer.get_topological_features(node_id)
                self.stats["topological_effects"][cycle_data["cycle_id"]] = topo_features
        
        # Enregistrer les statistiques mises à jour
        self._save_stats()
        
        # Générer un rapport de performance
        return self.generate_performance_report()
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Génère un rapport de performance basé sur les données historiques.
        
        Returns:
            Rapport de performance
        """
        # Obtenir les statistiques de base
        report = {
            "total_cycles": len(self.stats["cycles"]),
            "max_consecutive_wins": max(self.stats["heuristic_streaks"] or [0]), 
            "current_streak": self.stats["current_streak"],
            "win_ratio": 0,
            "average_multiplier": 0,
            "volatility_ratio": {},
            "topological_impact": {}
        }
        
        # Calculer le taux de victoire de l'heuristique
        wins = sum(1 for cycle in self.stats["cycles"] if cycle.get("winner") == "heuristic")
        if self.stats["cycles"]:
            report["win_ratio"] = wins / len(self.stats["cycles"])
        
        # Calculer le multiplicateur moyen
        if self.stats["multipliers"]:
            report["average_multiplier"] = sum(self.stats["multipliers"]) / len(self.stats["multipliers"])
        
        # Calculer le ratio volatilité/performance pour chaque stratégie
        for strategy, deltas in self.stats["volatility"].items():
            if len(deltas) >= 3:  # Besoin d'au moins 3 points pour calculer l'écart-type
                avg_delta = sum(deltas) / len(deltas)
                if avg_delta > 0:
                    # Utiliser l'écart-type comme mesure de volatilité
                    std_dev = statistics.stdev(deltas) if len(deltas) > 1 else 0
                    report["volatility_ratio"][strategy] = std_dev / avg_delta
        
        # Analyser l'impact des métriques topologiques
        if self.stats["topological_effects"]:
            topo_metrics = defaultdict(list)
            for cycle_id, features in self.stats["topological_effects"].items():
                for metric, value in features.items():
                    topo_metrics[metric].append(value)
            
            # Calculer les corrélations avec les performances
            for metric, values in topo_metrics.items():
                if len(values) > 1:
                    cycle_performances = [
                        cycle.get("heuristic_delta", 0) 
                        for cycle in self.stats["cycles"][-len(values):]
                    ]
                    if len(cycle_performances) == len(values):
                        correlation = statistics.correlation(values, cycle_performances)
                        report["topological_impact"][metric] = correlation
        
        # Ajouter les statistiques par période
        report["period_stats"] = self.dashboard.generate_statistical_report()
        
        return report
    
    def _save_stats(self):
        """Enregistre les statistiques dans un fichier JSON."""
        with open(self.performance_log, "w") as f:
            json.dump(self.stats, f, indent=2)
            
    def get_performance_plots(self) -> Dict[str, Any]:
        """Retourne les visualisations de performance pour différentes périodes"""
        return self.dashboard.generate_performance_plots()

class ActionEvaluator:
    """
    Évalue les actions et calcule les ajustements de poids avec des garde-fous 
    contre les biais et l'oscillation.
    """
    
    def __init__(self, data_dir: str = "collected_data", 
                 min_threshold: float = 0.15,
                 volatility_threshold: float = 0.5,
                 decay_rate: float = 0.8):
        """
        Initialise l'évaluateur d'actions.
        
        Args:
            data_dir: Répertoire des données
            min_threshold: Seuil minimal pour ajuster les poids (évite l'oscillation)
            volatility_threshold: Seuil de volatilité au-delà duquel réduire la sensibilité
            decay_rate: Taux de décroissance pour la moyenne mobile exponentiellement pondérée
        """
        self.data_dir = Path(data_dir)
        self.actions_dir = self.data_dir / "actions"
        self.min_threshold = min_threshold
        self.volatility_threshold = volatility_threshold
        self.decay_rate = decay_rate
        
        # Historique des ajustements pour calcul de moyenne mobile
        self.adjustment_history = []
        
        logger.info(f"ActionEvaluator initialisé avec seuil minimal={min_threshold}, " 
                  f"seuil de volatilité={volatility_threshold}")
    
    async def calculate_weight_adjustment(self, 
                                     winning_data: Dict[str, Any], 
                                     baseline_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Calcule l'ajustement des poids avec des garde-fous contre les oscillations.
        
        Args:
            winning_data: Données de l'action gagnante
            baseline_data: Données de la stratégie de référence (random)
            
        Returns:
            Nouveaux poids suggérés ou None si aucun ajustement nécessaire
        """
        # Vérifier si l'ajustement est nécessaire
        winning_delta = winning_data.get("delta_24h", 0)
        baseline_delta = baseline_data.get("delta_24h", 0)
        
        # Calculer le gain relatif
        if baseline_delta <= 0:
            relative_gain = 1.0  # Si baseline <= 0, tout gain positif est significatif
        else:
            relative_gain = (winning_delta - baseline_delta) / baseline_delta
        
        logger.info(f"Gain relatif: {relative_gain:.2f} (seuil: {self.min_threshold})")
        
        # Si le gain est inférieur au seuil, pas d'ajustement
        if relative_gain < self.min_threshold:
            logger.info(f"Gain trop faible pour ajuster les poids (sous le seuil de {self.min_threshold})")
            return None
        
        # Calculer la volatilité de la stratégie gagnante
        volatility = self._calculate_volatility(winning_data.get("scenario_id"))
        
        # Ajuster la sensibilité selon la volatilité
        sensitivity_factor = 1.0
        if volatility > self.volatility_threshold:
            logger.warning(f"Haute volatilité détectée: {volatility:.2f}. Réduction de la sensibilité.")
            sensitivity_factor = max(0.3, 1.0 - (volatility - self.volatility_threshold))
        
        # Extraire les métriques pour l'ajustement des poids
        metrics_before = winning_data.get("metrics_before", {})
        metrics_after = winning_data.get("metrics_after", {})
        
        # Calculer les corrélations entre les métriques et le delta
        correlations = {}
        
        metrics_to_analyze = [
            "htlc_response_time", 
            "channel_balance_quality", 
            "routing_success_rate", 
            "revenue_per_sat_locked",
            "liquid_channels_ratio",
            "bidirectional_channels_ratio"
        ]
        
        # Récupérer l'historique des dernières actions pour analyse
        recent_actions = await self._get_recent_actions(5)
        
        # Calculer les corrélations approximatives
        for metric in metrics_to_analyze:
            if metric in metrics_before and metric in metrics_after:
                # Calcul naïf de corrélation basé sur le changement de la métrique
                metric_delta = metrics_after[metric] - metrics_before[metric]
                
                # Une corrélation positive signifie que l'augmentation de la métrique 
                # est associée à une augmentation des sats forwardés
                if abs(metric_delta) > 0.001:  # Éviter division par zéro
                    correlation = winning_delta / metric_delta if metric_delta != 0 else 0
                    
                    # Normaliser la corrélation
                    correlation = max(-1.0, min(1.0, correlation))
                    correlations[metric] = correlation
        
        # Calculer les poids suggérés basés sur les corrélations
        suggested_weights = {
            "htlc_response_time": 0.30,      # Valeurs par défaut
            "liquidity_balance": 0.30,
            "routing_success_rate": 0.20,
            "revenue_efficiency": 0.10,
            "liquidity_score": 0.10
        }
        
        # Convertir les corrélations en ajustements de poids
        # Les métriques fortement corrélées avec le succès devraient avoir plus de poids
        weight_adjustments = {}
        
        # Mapper les corrélations aux poids
        if "htlc_response_time" in correlations:
            weight_adjustments["htlc_response_time"] = abs(correlations["htlc_response_time"]) * 0.1
        
        if "channel_balance_quality" in correlations:
            weight_adjustments["liquidity_balance"] = abs(correlations["channel_balance_quality"]) * 0.1
        
        if "routing_success_rate" in correlations:
            weight_adjustments["routing_success_rate"] = abs(correlations["routing_success_rate"]) * 0.1
        
        if "revenue_per_sat_locked" in correlations:
            weight_adjustments["revenue_efficiency"] = abs(correlations["revenue_per_sat_locked"]) * 0.1
        
        # Appliquer les ajustements avec le facteur de sensibilité
        for key, adjustment in weight_adjustments.items():
            suggested_weights[key] += adjustment * sensitivity_factor
        
        # Normaliser pour que la somme soit toujours 1.0
        total = sum(suggested_weights.values())
        normalized_weights = {k: v / total for k, v in suggested_weights.items()}
        
        # Ajouter à l'historique pour moyenne mobile
        self.adjustment_history.append(normalized_weights)
        if len(self.adjustment_history) > 5:
            self.adjustment_history.pop(0)
        
        # Calculer la moyenne mobile exponentiellement pondérée
        final_weights = self._compute_ema_weights()
        
        # Arrondir les poids pour lisibilité
        return {k: round(v, 2) for k, v in final_weights.items()}
    
    def _compute_ema_weights(self) -> Dict[str, float]:
        """
        Calcule la moyenne mobile exponentiellement pondérée des poids.
        
        Returns:
            Poids moyens pondérés
        """
        if not self.adjustment_history:
            return {}
        
        # Si un seul élément, le retourner directement
        if len(self.adjustment_history) == 1:
            return self.adjustment_history[0]
        
        # Calculer les poids pour chaque ajustement (plus récent = plus de poids)
        weights = [self.decay_rate ** i for i in range(len(self.adjustment_history) - 1, -1, -1)]
        weight_sum = sum(weights)
        
        # Initialiser le résultat avec les clés du dernier ajustement
        result = {k: 0.0 for k in self.adjustment_history[-1].keys()}
        
        # Calculer la moyenne pondérée
        for i, adjustment in enumerate(self.adjustment_history):
            weight = weights[i] / weight_sum
            for k, v in adjustment.items():
                if k in result:
                    result[k] += v * weight
        
        return result
    
    def _calculate_volatility(self, scenario_id: str) -> float:
        """
        Calcule la volatilité des performances d'un scénario.
        
        Args:
            scenario_id: ID du scénario
            
        Returns:
            Score de volatilité (0-1, plus élevé = plus volatile)
        """
        # Récupérer l'historique des deltas pour ce scénario
        deltas = []
        
        # Parcourir les fichiers d'action pour ce scénario
        for action_file in self.actions_dir.glob(f"{scenario_id}_*.json"):
            try:
                with open(action_file, "r") as f:
                    action_data = json.load(f)
                    
                    # Si le delta est disponible, l'ajouter à la liste
                    if "delta_24h" in action_data and action_data["delta_24h"] is not None:
                        deltas.append(action_data["delta_24h"])
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de {action_file}: {e}")
        
        # S'il n'y a pas assez de données, retourner une volatilité moyenne
        if len(deltas) < 2:
            return 0.5
        
        # Calculer la volatilité (coefficient de variation)
        mean = sum(deltas) / len(deltas)
        
        # Éviter division par zéro
        if mean == 0:
            return 1.0  # Volatilité maximale si moyenne nulle
            
        variance = sum((x - mean) ** 2 for x in deltas) / len(deltas)
        std_dev = math.sqrt(variance)
        
        # Normaliser entre 0 et 1
        return min(1.0, std_dev / abs(mean))
    
    async def _get_recent_actions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Récupère les actions récentes avec leurs résultats.
        
        Args:
            count: Nombre d'actions à récupérer
            
        Returns:
            Liste des données d'action
        """
        # Trouver tous les fichiers d'action
        action_files = list(self.actions_dir.glob("*.json"))
        
        # Trier par date de modification (plus récent d'abord)
        action_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Limiter au nombre demandé
        action_files = action_files[:count]
        
        # Charger les données
        actions = []
        for file in action_files:
            try:
                with open(file, "r") as f:
                    action_data = json.load(f)
                    
                    # Ne garder que les actions avec des résultats
                    if "metrics_after" in action_data and "delta_24h" in action_data:
                        actions.append(action_data)
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de {file}: {e}")
        
        return actions

# Classe pour tracker les actions et leurs résultats
class ActionTracker:
    """
    Système de suivi des actions recommandées et de leurs résultats.
    Implémente la boucle de feedback pour l'heuristique.
    """
    
    def __init__(self, data_dir: str = "collected_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Créer le répertoire pour les logs d'actions si nécessaire
        self.actions_dir = self.data_dir / "actions"
        self.actions_dir.mkdir(exist_ok=True, parents=True)
        
        # Fichier de métriques pour l'A/B testing
        self.metrics_file = self.data_dir / "metrics_comparison.csv"
        self.ensure_metrics_file_exists()
        
        # Initialiser l'évaluateur d'actions et le tracker de performance
        self.evaluator = ActionEvaluator(data_dir)
        self.performance_tracker = PerformanceTracker(data_dir)
        
        # Groupes de scénarios actuellement en test
        self.current_test_groups = defaultdict(list)
        
        logger.info(f"ActionTracker initialisé avec répertoire de données: {self.data_dir}")
    
    def ensure_metrics_file_exists(self):
        """S'assure que le fichier CSV de métriques existe avec les en-têtes appropriés."""
        if not self.metrics_file.exists():
            with open(self.metrics_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "node_id", "scenario_id", "scenario_type",
                    "sats_forwarded_24h_before", "sats_forwarded_24h_after", 
                    "sats_forwarded_48h_after", "delta_24h", "delta_48h",
                    "htlc_time_before", "htlc_time_after",
                    "success_rate_before", "success_rate_after",
                    "channel_balance_before", "channel_balance_after",
                    "is_winner", "cycle_id", "test_group"
                ])
    
    def log_action(self, node_id: str, scenario_id: str, action_type: str, 
                 metrics_before: Dict[str, Any], config: Dict[str, Any], 
                 test_group: str = "default") -> str:
        """
        Enregistre une action et ses métriques initiales.
        
        Args:
            node_id: ID du nœud
            scenario_id: ID du scénario
            action_type: Type d'action (heuristique, random, baseline)
            metrics_before: Métriques avant l'action
            config: Configuration appliquée
            test_group: Groupe de test pour l'A/B testing
            
        Returns:
            ID de l'action pour le suivi ultérieur
        """
        timestamp = datetime.now().isoformat()
        action_id = f"{scenario_id}_{timestamp.replace(':', '-')}"
        
        # Ajouter ce scénario au groupe de test actuel
        self.current_test_groups[test_group].append(scenario_id)
        
        action_data = {
            "action_id": action_id,
            "node_id": node_id,
            "scenario_id": scenario_id,
            "action_type": action_type,
            "timestamp_start": timestamp,
            "metrics_before": metrics_before,
            "config_applied": config,
            "metrics_after": {},
            "timestamp_update": None,
            "delta_24h": None,
            "delta_48h": None,
            "delta_7d": None,
            "test_group": test_group,
            "cycle_id": f"cycle_{int(datetime.now().timestamp())}"
        }
        
        # Enregistrer l'action dans un fichier JSON
        action_file = self.actions_dir / f"{action_id}.json"
        with open(action_file, "w") as f:
            json.dump(action_data, f, indent=2)
            
        logger.info(f"Action {action_id} enregistrée pour le nœud {node_id} (groupe {test_group})")
        return action_id
    
    async def update_action_results(self, action_id: str, metrics_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour les résultats d'une action avec les métriques après exécution.
        
        Args:
            action_id: ID de l'action à mettre à jour
            metrics_after: Métriques après l'action
            
        Returns:
            Données complètes de l'action mise à jour
        """
        action_file = self.actions_dir / f"{action_id}.json"
        
        if not action_file.exists():
            logger.error(f"Action {action_id} non trouvée pour mise à jour")
            return None
            
        # Charger les données existantes
        with open(action_file, "r") as f:
            action_data = json.load(f)
        
        # Calculer les deltas
        metrics_before = action_data.get("metrics_before", {})
        
        # Calculer le delta pour les sats forwardés (principale métrique de succès)
        sats_before = metrics_before.get("sats_forwarded_24h", 0)
        sats_after = metrics_after.get("sats_forwarded_24h", 0)
        delta_24h = sats_after - sats_before
        
        # Calculer le delta pour 7 jours si disponible
        sats_7d_before = metrics_before.get("sats_forwarded_7d", 0)
        sats_7d_after = metrics_after.get("sats_forwarded_7d", 0)
        delta_7d = sats_7d_after - sats_7d_before
        
        # Mettre à jour les données
        action_data["metrics_after"] = metrics_after
        action_data["timestamp_update"] = datetime.now().isoformat()
        action_data["delta_24h"] = delta_24h
        action_data["delta_7d"] = delta_7d
        
        # Enregistrer les données mises à jour
        with open(action_file, "w") as f:
            json.dump(action_data, f, indent=2)
        
        # Ajouter au fichier CSV de comparaison
        self.add_to_metrics_comparison(action_data)
            
        logger.info(f"Action {action_id} mise à jour avec delta de {delta_24h} sats forwardés (7j: {delta_7d})")
        
        # Vérifier si tous les scénarios du groupe de test ont été mis à jour
        test_group = action_data.get("test_group", "default")
        scenario_id = action_data.get("scenario_id")
        
        # Si ce scénario fait partie d'un groupe de test, vérifier si le groupe est complet
        if test_group in self.current_test_groups and scenario_id in self.current_test_groups[test_group]:
            await self._check_test_group_completion(test_group)
        
        return action_data
    
    async def _check_test_group_completion(self, test_group: str):
        """
        Vérifie si tous les scénarios d'un groupe de test ont été évalués.
        Si oui, identifie le gagnant et calcule les nouveaux poids.
        
        Args:
            test_group: Groupe de test à vérifier
        """
        scenario_ids = self.current_test_groups.get(test_group, [])
        if not scenario_ids:
            return
        
        # Vérifier si tous les scénarios ont des résultats
        all_scenarios_evaluated = True
        scenario_results = {}
        
        for scenario_id in scenario_ids:
            # Trouver le fichier d'action le plus récent pour ce scénario
            action_files = list(self.actions_dir.glob(f"{scenario_id}_*.json"))
            if not action_files:
                all_scenarios_evaluated = False
                break
                
            latest_file = max(action_files, key=lambda p: p.stat().st_mtime)
            
            with open(latest_file, "r") as f:
                action_data = json.load(f)
                
            # Vérifier si les résultats sont disponibles
            if "delta_24h" not in action_data or action_data["delta_24h"] is None:
                all_scenarios_evaluated = False
                break
                
            scenario_results[scenario_id] = action_data
        
        # Si tous les scénarios ont été évalués, identifier le gagnant
        if all_scenarios_evaluated and scenario_results:
            # Trouver le scénario avec le meilleur delta
            winner = max(scenario_results.items(), key=lambda x: x[1].get("delta_24h", 0))
            winner_id, winner_data = winner
            
            # Marquer le gagnant
            self.update_winner(winner_data["action_id"])
            
            logger.info(f"Groupe de test {test_group} complété. " 
                      f"Scénario gagnant: {winner_id} ({winner_data.get('action_type')}) " 
                      f"avec delta={winner_data.get('delta_24h', 0)}")
            
            # Trouver les données de référence (random)
            baseline_data = None
            for _, data in scenario_results.items():
                if data.get("action_type") == "random":
                    baseline_data = data
                    break
            
            # Si le gagnant n'est pas l'heuristique et que nous avons les données de référence,
            # calculer de nouveaux poids
            if winner_data.get("action_type") != "heuristic" and baseline_data:
                new_weights = await self.evaluator.calculate_weight_adjustment(winner_data, baseline_data)
                
                if new_weights:
                    logger.info(f"Nouveaux poids suggérés: {new_weights}")
                    
                    # Enregistrer les nouveaux poids
                    weights_file = self.data_dir / "heuristic_weights.json"
                    with open(weights_file, "w") as f:
                        json.dump({
                            "weights": new_weights,
                            "timestamp": datetime.now().isoformat(),
                            "winning_scenario": winner_id,
                            "winning_type": winner_data.get("action_type"),
                            "test_group": test_group
                        }, f, indent=2)
            
            # Créer des données pour le suivi des performances
            cycle_data = {
                "timestamp": datetime.now().isoformat(),
                "test_group": test_group,
                "winner": winner_data.get("action_type"),
                "cycle_id": winner_data.get("cycle_id")
            }
            
            # Ajouter les deltas pour chaque type de scénario
            for _, data in scenario_results.items():
                scenario_type = data.get("action_type")
                if scenario_type:
                    cycle_data[f"{scenario_type}_delta"] = data.get("delta_24h", 0)
            
            # Mettre à jour les statistiques de performance
            performance_report = self.performance_tracker.track_cycle(cycle_data)
            logger.info(f"Rapport de performance mis à jour: "
                      f"Max victoires consécutives={performance_report.get('max_consecutive_wins')}, "
                      f"Ratio de victoire={performance_report.get('win_ratio', 0):.2f}, "
                      f"Multiplicateur moyen={performance_report.get('average_multiplier', 0):.2f}x")
            
            # Effacer ce groupe de test des groupes actifs
            if test_group in self.current_test_groups:
                del self.current_test_groups[test_group]
    
    def add_to_metrics_comparison(self, action_data: Dict[str, Any]):
        """Ajoute les données d'une action au fichier CSV de comparaison."""
        metrics_before = action_data.get("metrics_before", {})
        metrics_after = action_data.get("metrics_after", {})
        
        row = [
            action_data.get("timestamp_start"),
            action_data.get("node_id"),
            action_data.get("scenario_id"),
            action_data.get("action_type"),
            metrics_before.get("sats_forwarded_24h", 0),
            metrics_after.get("sats_forwarded_24h", 0),
            metrics_after.get("sats_forwarded_48h", 0),
            action_data.get("delta_24h", 0),
            action_data.get("delta_48h", 0),
            metrics_before.get("htlc_response_time", 0),
            metrics_after.get("htlc_response_time", 0),
            metrics_before.get("routing_success_rate", 0),
            metrics_after.get("routing_success_rate", 0),
            metrics_before.get("channel_balance_quality", 0),
            metrics_after.get("channel_balance_quality", 0),
            False,  # is_winner par défaut à False, mis à jour séparément
            action_data.get("cycle_id", ""),
            action_data.get("test_group", "default")
        ]
        
        with open(self.metrics_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    async def identify_winners(self, scenario_group: List[str]) -> Dict[str, Any]:
        """
        Identifie les scénarios gagnants parmi un groupe de scénarios testés.
        
        Args:
            scenario_group: Liste des IDs de scénarios à comparer
            
        Returns:
            Dictionnaire avec le scénario gagnant et ses métriques
        """
        scenarios_data = []
        
        # Charger les données de chaque scénario
        for scenario_id in scenario_group:
            files = list(self.actions_dir.glob(f"{scenario_id}_*.json"))
            if not files:
                continue
                
            # Prendre le fichier le plus récent si plusieurs existent
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            
            with open(latest_file, "r") as f:
                scenario_data = json.load(f)
                
            if "delta_24h" in scenario_data and scenario_data["delta_24h"] is not None:
                scenarios_data.append(scenario_data)
        
        if not scenarios_data:
            logger.warning(f"Aucune donnée disponible pour les scénarios {scenario_group}")
            return None
            
        # Identifier le scénario avec le meilleur delta de sats forwardés
        winner = max(scenarios_data, key=lambda x: x.get("delta_24h", 0))
        
        # Marquer le gagnant dans le CSV
        self.update_winner(winner["action_id"])
        
        logger.info(f"Scénario gagnant identifié: {winner['scenario_id']} avec un delta de {winner['delta_24h']} sats")
        return winner
    
    def update_winner(self, action_id: str):
        """Marque un scénario comme gagnant dans le CSV de métriques."""
        # Extraire l'ID du scénario et le cycle à partir de l'ID d'action
        parts = action_id.split("_", 1)
        if len(parts) < 2:
            logger.error(f"Format d'ID d'action invalide: {action_id}")
            return
            
        scenario_id = parts[0]
        
        # Charger les données d'action pour obtenir le cycle_id
        action_file = self.actions_dir / f"{action_id}.json"
        cycle_id = ""
        
        try:
            with open(action_file, "r") as f:
                action_data = json.load(f)
                cycle_id = action_data.get("cycle_id", "")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {action_file}: {e}")
        
        # Lire le fichier CSV
        rows = []
        try:
            with open(self.metrics_file, "r", newline="") as f:
                reader = csv.reader(f)
                header = next(reader)  # Conserver l'en-tête
                
                # Trouver l'index de la colonne is_winner
                winner_idx = header.index("is_winner") if "is_winner" in header else -1
                scenario_idx = header.index("scenario_id") if "scenario_id" in header else -1
                cycle_idx = header.index("cycle_id") if "cycle_id" in header else -1
                
                if winner_idx == -1 or scenario_idx == -1:
                    logger.error("Colonnes requises non trouvées dans le CSV")
                    return
                
                # Mettre à jour la ligne correspondante
                for row in reader:
                    # Si c'est une ligne du même cycle et du même scénario, marquer comme gagnant
                    if (cycle_idx != -1 and cycle_id and row[cycle_idx] == cycle_id and 
                        row[scenario_idx] == scenario_id):
                        row[winner_idx] = "True"
                    
                    rows.append(row)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du CSV: {e}")
            return
        
        # Réécrire le fichier avec les données mises à jour
        try:
            with open(self.metrics_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
                
            logger.info(f"Action {action_id} marquée comme gagnante dans le CSV")
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture du CSV: {e}")
    
    async def get_latest_weights(self) -> Dict[str, float]:
        """
        Récupère les poids les plus récents pour l'heuristique.
        
        Returns:
            Poids actuels de l'heuristique
        """
        weights_file = self.data_dir / "heuristic_weights.json"
        
        # Si le fichier existe, charger les poids
        if weights_file.exists():
            try:
                with open(weights_file, "r") as f:
                    data = json.load(f)
                    return data.get("weights", {})
            except Exception as e:
                logger.error(f"Erreur lors de la lecture des poids: {e}")
        
        # Poids par défaut si pas de fichier
        return {
            "htlc_response_time": 0.35,  # Valeurs par défaut ajustées
            "liquidity_balance": 0.30,
            "routing_success_rate": 0.25,
            "revenue_efficiency": 0.05,
            "liquidity_score": 0.05
        }


class TestScenarioManager:
    def __init__(self, lnbits_client: LNBitsClient):
        self.lnbits_client = lnbits_client
        self.active_tests = {}
        self.test_metrics = {}
        self.action_tracker = ActionTracker()

    async def configure_node(self, scenario: Dict[str, Any]) -> bool:
        """
        Configure le nœud selon le scénario donné.
        
        Args:
            scenario: Configuration du scénario
            
        Returns:
            True si la configuration a réussi, False sinon
        """
        try:
            # Obtenir l'ID du nœud
            node_id = await self._get_node_id()
            if not node_id:
                logger.error("Impossible de récupérer l'ID du nœud")
                return False
                
            # Obtenir les métriques actuelles
            metrics_before = await self.get_current_metrics()
            
            # Configurer les frais de base et le taux
            fee_structure = scenario.get("fee_structure", {})
            base_fee = fee_structure.get("base_fee_msat", 1000)
            fee_rate = fee_structure.get("fee_rate", 100)
            
            # Enregistrer l'action
            action_id = self.action_tracker.log_action(
                node_id=node_id,
                scenario_id=scenario["id"],
                action_type="configure",
                metrics_before=metrics_before,
                config=scenario
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du nœud: {str(e)}")
            return False
    
    async def _get_node_id(self) -> str:
        """
        Récupère l'ID du nœud local.
        
        Returns:
            ID du nœud
        """
        try:
            info = await self.lnbits_client._make_request("GET", "/api/v1/wallet", admin=True)
            return info.get("id", "")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'ID du nœud: {str(e)}")
            raise
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        Récupère les métriques actuelles du nœud.
        
        Returns:
            Métriques du nœud
        """
        try:
            # Obtenir les informations du wallet
            wallet_info = await self.lnbits_client._make_request("GET", "/api/v1/wallet", admin=True)
            
            # Obtenir l'historique des paiements
            payments = await self.lnbits_client._make_request("GET", "/api/v1/payments", admin=True)
            
            # Calculer les métriques
            metrics = {
                "balance": wallet_info.get("balance", 0),
                "total_payments": len(payments) if isinstance(payments, list) else 0,
                "successful_forwards": sum(1 for p in payments if p.get("status") == "complete") if isinstance(payments, list) else 0,
                "balance_quality": 0.5  # Valeur par défaut en attendant l'implémentation des canaux
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
            raise
            
    async def start_test_session(self, scenario_id: str, duration_minutes: int = 60, payment_count: int = 50) -> str:
        """
        Démarre une session de test pour un scénario.
        
        Args:
            scenario_id: Identifiant du scénario à tester
            duration_minutes: Durée du test en minutes
            payment_count: Nombre de paiements à simuler
            
        Returns:
            ID du test créé
        """
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        
        # Enregistrer les détails du test
        self.active_tests[test_id] = {
            "scenario_id": scenario_id,
            "start_time": datetime.now(),
            "duration_minutes": duration_minutes,
            "payment_count": payment_count,
            "test_payments_sent": 0,
            "action_id": self.active_tests.get(scenario_id, {}).get("action_id", "")
        }
        
        # Simuler le démarrage d'un test (dans un système réel, ce serait un appel à LNBits)
        await self._simulate_test_traffic(test_id, payment_count)
        
        return test_id
        
    async def _simulate_test_traffic(self, test_id: str, payment_count: int):
        """Simule le trafic de paiements pour un test."""
        # Dans un système réel, cette méthode démarrerait des paiements réels
        # Pour cette démonstration, nous simulons simplement l'envoi
        self.active_tests[test_id]["test_payments_sent"] = payment_count
        print(f"Test {test_id}: Simulation de {payment_count} paiements démarrée")
        
    async def get_test_metrics(self, test_id: str) -> Dict[str, Any]:
        """
        Récupère les métriques d'un test en cours ou terminé.
        
        Args:
            test_id: ID du test
            
        Returns:
            Métriques du test
        """
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} non trouvé")
            
        # Dans un système réel, nous récupérerions les métriques actuelles du nœud
        # Pour cette démonstration, nous simulons des métriques basées sur le temps écoulé
        test_info = self.active_tests[test_id]
        elapsed_minutes = (datetime.now() - test_info["start_time"]).total_seconds() / 60
        
        # Récupérer les métriques réelles
        current_metrics = await self.get_current_metrics()
        
        # Si le test est terminé, mettre à jour les résultats dans l'ActionTracker
        action_id = test_info.get("action_id")
        if action_id and elapsed_minutes >= test_info["duration_minutes"]:
            await self.action_tracker.update_action_results(action_id, current_metrics)
        
        return current_metrics
        
    def _calculate_balance_quality(self, channels: List[Dict[str, Any]]) -> float:
        """
        Calcule la qualité d'équilibre des canaux.
        
        Args:
            channels: Liste des canaux du nœud
            
        Returns:
            Score de qualité d'équilibre (0-1)
        """
        if not channels:
            return 0.5  # Valeur par défaut
            
        balance_scores = []
        
        for channel in channels:
            local_balance = channel.get("local_balance", 0)
            remote_balance = channel.get("remote_balance", 0)
            capacity = local_balance + remote_balance
            
            if capacity == 0:
                continue
                
            # Calcul de l'équilibre: 1.0 = parfaitement équilibré, 0.0 = totalement déséquilibré
            local_ratio = local_balance / capacity
            # Idéal = 0.5 (50% local, 50% distant)
            balance_score = 1.0 - abs(local_ratio - 0.5) * 2
            balance_scores.append(balance_score)
            
        if not balance_scores:
            return 0.5
            
        return sum(balance_scores) / len(balance_scores)
        
    async def cleanup_tests(self):
        """Nettoie les tests actifs et génère un rapport final."""
        # Récupérer tous les tests actifs
        active_test_ids = list(self.active_tests.keys())
        
        for test_id in active_test_ids:
            test_info = self.active_tests[test_id]
            action_id = test_info.get("action_id")
            
            if action_id:
                # Récupérer les métriques finales
                final_metrics = await self.get_current_metrics()
                # Mettre à jour les résultats dans l'ActionTracker
                await self.action_tracker.update_action_results(action_id, final_metrics)
            
            # Supprimer le test de la liste des tests actifs
            del self.active_tests[test_id]
            
        print(f"Nettoyage terminé: {len(active_test_ids)} tests finalisés")
        
    async def generate_a_b_test(self, base_scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Génère des scénarios pour A/B testing.
        
        Args:
            base_scenario: Scénario de base à tester
            
        Returns:
            Liste de scénarios: [heuristique, random, baseline]
        """
        scenarios = []
        
        # 1. Scénario basé sur l'heuristique (le scénario de base)
        base_scenario["type"] = "heuristic"
        base_scenario["id"] = f"heuristic_{uuid.uuid4().hex[:8]}"
        scenarios.append(base_scenario)
        
        # 2. Scénario aléatoire
        random_scenario = self._generate_random_scenario()
        random_scenario["type"] = "random"
        random_scenario["id"] = f"random_{uuid.uuid4().hex[:8]}"
        scenarios.append(random_scenario)
        
        # 3. Scénario baseline (simple maximisation des fees)
        baseline_scenario = {
            "id": f"baseline_{uuid.uuid4().hex[:8]}",
            "type": "baseline",
            "name": "Maximisation des frais simple",
            "description": "Configuration qui maximise uniquement les frais sans optimisation complexe",
            "fee_structure": {
                "base_fee_msat": 5000,
                "fee_rate": 500
            },
            "channel_policy": {
                "target_local_ratio": 0.5,
                "rebalance_threshold": 0.2
            }
        }
        scenarios.append(baseline_scenario)
        
        return scenarios
        
    def _generate_random_scenario(self) -> Dict[str, Any]:
        """Génère un scénario avec des paramètres aléatoires."""
        import random
        
        return {
            "name": "Configuration aléatoire",
            "description": "Paramètres générés aléatoirement pour comparaison",
            "fee_structure": {
                "base_fee_msat": random.randint(500, 10000),
                "fee_rate": random.randint(50, 1000)
            },
            "channel_policy": {
                "target_local_ratio": random.uniform(0.3, 0.7),
                "rebalance_threshold": random.uniform(0.1, 0.4)
            },
            "peer_selection": {
                "min_capacity": random.randint(50000, 500000)
            }
        } 