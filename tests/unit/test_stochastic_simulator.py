#!/usr/bin/env python3
"""
Tests unitaires pour le simulateur stochastique de nœuds Lightning.

Dernière mise à jour: 7 mai 2025
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
import random
import numpy as np
from typing import Dict, Any, List

# Ajuster le chemin d'imports pour les tests
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.tools.simulator.performance_metrics import PerformanceMetrics
from src.tools.simulator.channel_evolution import StochasticChannelEvolution
from src.tools.simulator.scenario_matrix import ScenarioMatrix
from src.tools.simulator.simulation_fixtures import SimulationFixtures
from src.tools.simulator.stochastic_simulator import (
    LightningSimEnvironment, DecisionEvaluator, DummyDecisionEngine
)


class TestPerformanceMetrics(unittest.TestCase):
    """Tests pour la classe PerformanceMetrics"""
    
    def setUp(self):
        """Initialiser les objets pour les tests"""
        self.metrics = PerformanceMetrics()
    
    def test_update_metrics(self):
        """Tester la mise à jour des métriques"""
        # Valeurs initiales
        self.assertEqual(self.metrics.metrics["revenue"], 0)
        
        # Mettre à jour les métriques
        new_metrics = {
            "revenue": 1000,
            "opportunity_cost": 100,
            "capital_efficiency": 0.7
        }
        self.metrics.update_metrics(new_metrics)
        
        # Vérifier les mises à jour
        self.assertEqual(self.metrics.metrics["revenue"], 1000)
        self.assertEqual(self.metrics.metrics["opportunity_cost"], 100)
        self.assertEqual(self.metrics.metrics["capital_efficiency"], 0.7)
        
        # Vérifier que l'historique a été mis à jour
        self.assertEqual(len(self.metrics.history), 1)
    
    def test_calculate_decision_impact(self):
        """Tester le calcul de l'impact des décisions"""
        before_state = {
            "revenue": 1000,
            "opportunity_cost": 100,
            "capital_efficiency": 0.5,
            "htlc_success_rate": 0.9,
            "rebalancing_cost": 50
        }
        
        after_state = {
            "revenue": 1200,
            "opportunity_cost": 80,
            "capital_efficiency": 0.6,
            "htlc_success_rate": 0.95,
            "rebalancing_cost": 40
        }
        
        impact = self.metrics.calculate_decision_impact(before_state, after_state, timeframe=1)
        
        # Vérifier que l'impact contient les deltas et un score global
        self.assertIn("revenue_delta", impact)
        self.assertIn("opportunity_cost_delta", impact)
        self.assertIn("capital_efficiency_delta", impact)
        self.assertIn("effectiveness_score", impact)
        
        # Vérifier les valeurs calculées
        self.assertAlmostEqual(impact["revenue_delta"], 0.2, places=6)  # +20%
        self.assertAlmostEqual(impact["opportunity_cost_delta"], -0.2, places=6)  # -20%
        self.assertAlmostEqual(impact["capital_efficiency_delta"], 0.2, places=6)  # +20%
        
        # Vérifier que le score d'efficacité est positif et dans la plage [0, 10]
        self.assertGreater(impact["effectiveness_score"], 0)
        self.assertLessEqual(impact["effectiveness_score"], 10)
    
    def test_reset(self):
        """Tester la réinitialisation des métriques"""
        # Mettre à jour les métriques
        new_metrics = {"revenue": 1000}
        self.metrics.update_metrics(new_metrics)
        
        # Vérifier que les métriques sont mises à jour
        self.assertEqual(self.metrics.metrics["revenue"], 1000)
        self.assertEqual(len(self.metrics.history), 1)
        
        # Réinitialiser
        self.metrics.reset()
        
        # Vérifier la réinitialisation
        self.assertEqual(self.metrics.metrics["revenue"], 0)
        self.assertEqual(len(self.metrics.history), 0)


class TestChannelEvolution(unittest.TestCase):
    """Tests pour la classe StochasticChannelEvolution"""
    
    def setUp(self):
        """Initialiser les objets pour les tests"""
        # Paramètres de base d'un canal
        self.base_parameters = {
            "channel_id": "test_channel_123",
            "capacity": 5000000,
            "local_balance": 2500000,
            "remote_balance": 2500000,
            "total_forwards": 100,
            "successful_forwards": 95,
            "local_fee_base_msat": 1000,
            "local_fee_rate": 500,
            "centrality_score": 0.5,
            "htlc_success_rate": 0.95,
            "active": True
        }
        
        # Facteurs de volatilité
        self.volatility_factors = {
            "volume": 0.1,
            "success_rate": 0.05,
            "liquidity": 0.2,
            "noise": 0.05
        }
        
        # Créer l'objet d'évolution
        self.evolution = StochasticChannelEvolution(
            self.base_parameters, self.volatility_factors)
    
    def test_natural_evolution(self):
        """Tester l'évolution naturelle d'un canal"""
        # État initial
        initial_state = self.evolution.get_current_state()
        
        # Simuler un pas de temps
        next_state = self.evolution.simulate_step(time_delta=1)
        
        # Vérifier que l'état a changé
        self.assertNotEqual(initial_state["total_forwards"], next_state["total_forwards"])
        
        # Vérifier que l'historique a été mis à jour
        self.assertEqual(len(self.evolution.get_historical_states()), 2)
        
        # Vérifier que la capacité reste constante
        self.assertEqual(initial_state["capacity"], next_state["capacity"])
        
        # Vérifier que la somme des balances est égale à la capacité
        self.assertEqual(
            next_state["local_balance"] + next_state["remote_balance"],
            next_state["capacity"]
        )
    
    def test_policy_impact(self):
        """Tester l'impact d'un changement de politique sur l'évolution"""
        # État initial
        initial_state = self.evolution.get_current_state()
        initial_fee_rate = initial_state["local_fee_rate"]
        
        # Simuler un changement de politique - augmentation des frais de 20%
        policy_changes = {
            "fee_base_change": int(initial_state["local_fee_base_msat"] * 0.2 / 1000),
            "fee_rate_change": int(initial_state["local_fee_rate"] * 0.2)
        }
        
        # Appliquer le changement
        next_state = self.evolution.simulate_step(time_delta=0, policy_changes=policy_changes)
        
        # Vérifier que les frais ont augmenté
        self.assertGreater(next_state["local_fee_rate"], initial_fee_rate)
        
        # Simuler un autre pas pour voir l'impact sur les forwards
        final_state = self.evolution.simulate_step(time_delta=1)
        
        # La hausse des frais devrait généralement réduire le volume, mais c'est stochastique
        # Donc on ne peut pas faire d'assertion stricte ici


class TestScenarioMatrix(unittest.TestCase):
    """Tests pour la classe ScenarioMatrix"""
    
    def setUp(self):
        """Initialiser les objets pour les tests"""
        self.matrix = ScenarioMatrix()
    
    def test_generate_scenario_combinations(self):
        """Tester la génération de combinaisons de scénarios"""
        # Générer 5 scénarios
        scenarios = self.matrix.generate_scenario_combinations(sample_size=5)
        
        # Vérifier qu'on a le bon nombre de scénarios
        self.assertEqual(len(scenarios), 5)
        
        # Vérifier que chaque scénario a les bonnes clés
        for scenario in scenarios:
            self.assertIn("node_centrality", scenario)
            self.assertIn("volume_level", scenario)
            self.assertIn("liquidity_balance", scenario)
    
    def test_generate_channel_parameters(self):
        """Tester la génération de paramètres de canal"""
        scenario = {
            "node_centrality": 0.8,
            "volume_level": 500,
            "liquidity_balance": 0.6,
            "fee_policy": "aggressive",
            "network_volatility": 0.1,
            "channel_capacity": 10000000
        }
        
        channel = self.matrix.generate_channel_parameters(scenario)
        
        # Vérifier que les paramètres du canal reflètent le scénario
        self.assertEqual(channel["capacity"], 10000000)
        self.assertAlmostEqual(channel["local_balance"] / channel["capacity"], 0.6, places=1)
        self.assertGreater(channel["total_forwards"], 400)  # Proche de volume_level=500 avec bruit


class TestSimulationFixtures(unittest.TestCase):
    """Tests pour la classe SimulationFixtures"""
    
    def setUp(self):
        """Initialiser l'environnement temporaire pour les tests"""
        # Créer un répertoire temporaire pour les fixtures
        self.temp_dir = tempfile.mkdtemp()
        
        # Sauvegarder le chemin original
        self.original_path = SimulationFixtures.FIXTURES_PATH
        
        # Remplacer par le chemin temporaire
        SimulationFixtures.FIXTURES_PATH = Path(self.temp_dir)
    
    def tearDown(self):
        """Nettoyer après les tests"""
        # Restaurer le chemin original
        SimulationFixtures.FIXTURES_PATH = self.original_path
        
        # Supprimer le répertoire temporaire
        shutil.rmtree(self.temp_dir)
    
    def test_load_historical_patterns(self):
        """Tester le chargement des patterns historiques"""
        patterns = SimulationFixtures.load_historical_patterns("seasonal")
        
        # Vérifier que les patterns sont chargés correctement
        self.assertIn("weekly_cycle", patterns)
        self.assertIn("daily_cycle", patterns)
        self.assertEqual(len(patterns["weekly_cycle"]), 7)  # 7 jours dans une semaine
    
    def test_apply_controlled_noise(self):
        """Tester l'application de bruit contrôlé"""
        base_value = 100
        
        # Test avec distribution normale
        noisy_value = SimulationFixtures.apply_controlled_noise(
            base_value, noise_level=0.1, distribution="normal")
        
        # La valeur devrait être proche mais différente de la base
        self.assertNotEqual(noisy_value, base_value)
        self.assertAlmostEqual(noisy_value, base_value, delta=base_value * 0.3)  # Tolerance de 30%
    
    def test_generate_seasonal_data(self):
        """Tester la génération de données saisonnières"""
        base_value = 100
        days = 14
        
        # Générer des données saisonnières
        seasonal_data = SimulationFixtures.generate_seasonal_data(
            base_value, days, amplitude=0.2, noise_level=0.05)
        
        # Vérifier la longueur des données
        self.assertEqual(len(seasonal_data), days)
        
        # Vérifier que les valeurs oscillent autour de la base
        self.assertAlmostEqual(np.mean(seasonal_data), base_value, delta=base_value * 0.1)
    
    def test_save_and_load_fixture(self):
        """Tester la sauvegarde et le chargement de fixtures"""
        # Données de test
        test_data = {
            "name": "test_fixture",
            "values": [1, 2, 3, 4, 5],
            "metadata": {"created": "2025-05-07"}
        }
        
        # Sauvegarder la fixture
        success = SimulationFixtures.save_fixture(test_data, "test_fixture")
        self.assertTrue(success)
        
        # Charger la fixture
        loaded_data = SimulationFixtures.load_fixture("test_fixture")
        
        # Vérifier que les données sont correctement chargées
        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_data["name"], test_data["name"])
        self.assertEqual(loaded_data["values"], test_data["values"])


class TestSimpleDecisionEngine:
    """Moteur de décision simple pour les tests"""
    
    def evaluate_network(self, network_state):
        """
        Implémentation simple qui augmente les frais pour tous les canaux
        """
        decisions = []
        
        # Extraire les canaux du réseau
        if "network" in network_state and "channels" in network_state["network"]:
            channels = network_state["network"]["channels"]
            
            for channel in channels:
                channel_id = channel.get("channel_id", "unknown")
                
                # Décision arbitraire pour le test
                decision = {
                    "channel_id": channel_id,
                    "action": "INCREASE_FEES",
                    "fee_base_change": 100,
                    "fee_rate_change": 50
                }
                decisions.append(decision)
        
        return decisions


class TestLightningSimEnvironment(unittest.TestCase):
    """Tests pour la classe LightningSimEnvironment"""
    
    def setUp(self):
        """Initialiser les objets pour les tests"""
        # Configuration simplifiée pour les tests
        self.config = {
            "network_size": 5,
            "scenarios": [
                {
                    "node_centrality": 0.5,
                    "volume_level": 100,
                    "liquidity_balance": 0.5,
                    "fee_policy": "moderate",
                    "network_volatility": 0.2
                }
            ],
            "simulation_days": 5,
            "noise_level": 0.1,
            "save_results": False
        }
        
        # Créer l'environnement de simulation
        self.simulator = LightningSimEnvironment(self.config)
    
    def test_initialization(self):
        """Tester l'initialisation de l'environnement"""
        # Vérifier que le réseau est construit
        self.assertIn("nodes", self.simulator.network)
        self.assertIn("channels", self.simulator.network)
        
        # Vérifier que les métriques sont initialisées
        self.assertIsInstance(self.simulator.metrics_tracker, PerformanceMetrics)
    
    def test_run_simulation_dummy(self):
        """Tester l'exécution d'une simulation avec un moteur factice"""
        # Créer un moteur de décision factice
        dummy_engine = DummyDecisionEngine()
        
        # Exécuter la simulation
        results = self.simulator.run_simulation(steps=5, decision_engine=dummy_engine)
        
        # Vérifier les résultats
        self.assertIn("final_state", results)
        self.assertIn("final_metrics", results)
        self.assertIn("improvement_rate", results)
        self.assertIn("history", results)
        
        # Vérifier que l'historique contient le bon nombre d'entrées (initial + steps)
        self.assertEqual(len(results["history"]), 5 + 1)
    
    def test_run_simulation_with_decisions(self):
        """Tester l'exécution d'une simulation avec un moteur de décision"""
        # Créer un moteur de décision simple
        decision_engine = TestSimpleDecisionEngine()
        
        # Exécuter la simulation
        results = self.simulator.run_simulation(steps=5, decision_engine=decision_engine)
        
        # Vérifier les résultats
        self.assertIn("final_state", results)
        self.assertIn("final_metrics", results)
        
        # Vérifier que les métriques finales sont non nulles
        self.assertGreater(results["final_metrics"]["revenue"], 0)


class TestDecisionEvaluator(unittest.TestCase):
    """Tests pour la classe DecisionEvaluator"""
    
    def setUp(self):
        """Initialiser les objets pour les tests"""
        # Configuration simplifiée pour les tests
        config = {
            "network_size": 5,
            "scenarios": [
                {
                    "node_centrality": 0.5,
                    "volume_level": 100,
                    "liquidity_balance": 0.5,
                    "fee_policy": "moderate",
                    "network_volatility": 0.2
                }
            ],
            "simulation_days": 5,
            "noise_level": 0.1,
            "save_results": False
        }
        
        # Créer l'environnement de simulation
        simulator = LightningSimEnvironment(config)
        
        # Créer l'évaluateur
        self.evaluator = DecisionEvaluator(simulator)
    
    def test_run_baseline_simulation(self):
        """Tester l'exécution d'une simulation de référence"""
        # Exécuter la simulation de référence
        baseline_results = self.evaluator.run_baseline_simulation(steps=3)
        
        # Vérifier les résultats
        self.assertIn("final_state", baseline_results)
        self.assertIn("final_metrics", baseline_results)
        
        # Vérifier que la référence est stockée
        self.assertIsNotNone(self.evaluator.baseline_results)
    
    def test_evaluate_decision_engine(self):
        """Tester l'évaluation d'un moteur de décision"""
        # Créer un moteur de décision simple
        decision_engine = TestSimpleDecisionEngine()
        
        # Évaluer le moteur
        evaluation = self.evaluator.evaluate_decision_engine(decision_engine, steps=3)
        
        # Vérifier les résultats
        self.assertIn("results", evaluation)
        self.assertIn("baseline", evaluation)
        self.assertIn("comparison", evaluation)
        self.assertIn("recommendations", evaluation)
        
        # Vérifier la comparaison
        self.assertIn("decision_quality", evaluation["comparison"])
        
        # Vérifier les recommandations
        self.assertIsInstance(evaluation["recommendations"], list)


if __name__ == "__main__":
    # Exécuter les tests
    unittest.main() 