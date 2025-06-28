#!/usr/bin/env python3
"""
Tests unitaires pour le module DazFlow Index
Tests des calculs et analyses de métriques avancées

Dernière mise à jour: 7 mai 2025
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime

from src.analytics import DazFlowCalculator, DazFlowAnalysis, ReliabilityCurve

class TestDazFlowCalculator:
    """Tests pour le calculateur DazFlow Index"""
    
    def setup_method(self):
        """Initialise le calculateur pour chaque test"""
        self.calculator = DazFlowCalculator()
        
        # Données de test pour un nœud
        self.sample_node_data = {
            "node_id": "test_node_123",
            "channels": [
                {
                    "channel_id": "channel_1",
                    "peer_alias": "peer_1",
                    "capacity": 1000000,
                    "local_balance": 500000,
                    "remote_balance": 500000,
                    "active": True
                },
                {
                    "channel_id": "channel_2", 
                    "peer_alias": "peer_2",
                    "capacity": 2000000,
                    "local_balance": 1800000,
                    "remote_balance": 200000,
                    "active": True
                },
                {
                    "channel_id": "channel_3",
                    "peer_alias": "peer_3", 
                    "capacity": 500000,
                    "local_balance": 100000,
                    "remote_balance": 400000,
                    "active": True
                }
            ],
            "historical_success_rate": 0.85,
            "metrics": {
                "centrality": {
                    "betweenness": 0.6
                }
            }
        }
    
    def test_calculate_payment_success_probability_balanced(self):
        """Test du calcul de probabilité de succès avec canaux équilibrés"""
        amount = 100000
        probability = self.calculator.calculate_payment_success_probability(
            self.sample_node_data, amount
        )
        
        assert 0.0 <= probability <= 1.0
        assert probability > 0.5  # Devrait être élevée avec des canaux équilibrés
    
    def test_calculate_payment_success_probability_unbalanced(self):
        """Test avec des canaux déséquilibrés"""
        unbalanced_data = self.sample_node_data.copy()
        unbalanced_data["channels"] = [
            {
                "channel_id": "unbalanced_1",
                "peer_alias": "peer_1",
                "capacity": 1000000,
                "local_balance": 900000,
                "remote_balance": 100000,
                "active": True
            }
        ]
        
        amount = 500000
        probability = self.calculator.calculate_payment_success_probability(
            unbalanced_data, amount
        )
        
        assert probability < 0.8  # Devrait être plus faible
    
    def test_calculate_payment_success_probability_large_amount(self):
        """Test avec un montant très élevé"""
        amount = 10000000  # 10M sats
        probability = self.calculator.calculate_payment_success_probability(
            self.sample_node_data, amount
        )
        
        assert probability < 0.3  # Devrait être faible pour un montant élevé
    
    def test_generate_reliability_curve(self):
        """Test de génération de la courbe de fiabilité"""
        amounts = [1000, 10000, 100000, 1000000]
        curve = self.calculator.generate_reliability_curve(
            self.sample_node_data, amounts
        )
        
        assert isinstance(curve, ReliabilityCurve)
        assert len(curve.amounts) == len(amounts)
        assert len(curve.probabilities) == len(amounts)
        assert len(curve.confidence_intervals) == len(amounts)
        
        # Vérifier que les probabilités décroissent avec le montant
        for i in range(1, len(curve.probabilities)):
            assert curve.probabilities[i] <= curve.probabilities[i-1]
    
    def test_identify_bottlenecks(self):
        """Test d'identification des goulots d'étranglement"""
        bottlenecks = self.calculator.identify_bottlenecks(self.sample_node_data)
        
        assert isinstance(bottlenecks, list)
        
        # Vérifier que le canal déséquilibré est identifié
        unbalanced_channel = next(
            (b for b in bottlenecks if b["channel_id"] == "channel_2"), None
        )
        assert unbalanced_channel is not None
        assert "déséquilibre_liquidité" in unbalanced_channel["issues"]
        assert unbalanced_channel["severity"] == "high"
    
    def test_identify_bottlenecks_no_issues(self):
        """Test avec des canaux parfaitement équilibrés"""
        balanced_data = self.sample_node_data.copy()
        balanced_data["channels"] = [
            {
                "channel_id": "balanced_1",
                "peer_alias": "peer_1",
                "capacity": 1000000,
                "local_balance": 500000,
                "remote_balance": 500000,
                "active": True
            }
        ]
        
        bottlenecks = self.calculator.identify_bottlenecks(balanced_data)
        assert len(bottlenecks) == 0
    
    def test_analyze_dazflow_index(self):
        """Test d'analyse complète DazFlow Index"""
        analysis = self.calculator.analyze_dazflow_index(self.sample_node_data)
        
        assert isinstance(analysis, DazFlowAnalysis)
        assert analysis.node_id == "test_node_123"
        assert isinstance(analysis.timestamp, datetime)
        assert 0.0 <= analysis.dazflow_index <= 1.0
        assert 0.0 <= analysis.liquidity_efficiency <= 1.0
        assert 0.0 <= analysis.network_centrality <= 1.0
        assert len(analysis.payment_amounts) > 0
        assert len(analysis.success_probabilities) > 0
        assert len(analysis.bottleneck_channels) >= 0
    
    def test_analyze_dazflow_index_empty_channels(self):
        """Test avec un nœud sans canaux"""
        empty_data = {
            "node_id": "empty_node",
            "channels": [],
            "historical_success_rate": 0.85
        }
        
        analysis = self.calculator.analyze_dazflow_index(empty_data)
        assert analysis is None
    
    def test_calculate_available_flow(self):
        """Test du calcul de flux disponible"""
        amount = 100000
        available_flow = self.calculator._calculate_available_flow(
            self.sample_node_data["channels"], amount
        )
        
        assert available_flow > 0
        assert available_flow <= sum(c["capacity"] for c in self.sample_node_data["channels"])
    
    def test_calculate_liquidity_factor(self):
        """Test du calcul du facteur de liquidité"""
        amount = 100000
        factor = self.calculator._calculate_liquidity_factor(
            self.sample_node_data["channels"], amount
        )
        
        assert 0.0 <= factor <= 1.0
    
    def test_calculate_connectivity_factor(self):
        """Test du calcul du facteur de connectivité"""
        factor = self.calculator._calculate_connectivity_factor(self.sample_node_data)
        
        assert 0.0 <= factor <= 1.0
    
    def test_calculate_liquidity_efficiency(self):
        """Test du calcul de l'efficacité de liquidité"""
        efficiency = self.calculator._calculate_liquidity_efficiency(self.sample_node_data)
        
        assert 0.0 <= efficiency <= 1.0
    
    def test_error_handling_invalid_data(self):
        """Test de gestion des erreurs avec données invalides"""
        invalid_data = {
            "node_id": "invalid_node",
            "channels": [
                {
                    "channel_id": "invalid_channel",
                    "capacity": "invalid",  # Type invalide
                    "local_balance": None,
                    "remote_balance": "invalid"
                }
            ]
        }
        
        # Ces méthodes doivent gérer les erreurs gracieusement
        probability = self.calculator.calculate_payment_success_probability(
            invalid_data, 100000
        )
        assert probability == 0.0
        
        bottlenecks = self.calculator.identify_bottlenecks(invalid_data)
        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) == 0

class TestReliabilityCurve:
    """Tests pour la classe ReliabilityCurve"""
    
    def test_reliability_curve_creation(self):
        """Test de création d'une courbe de fiabilité"""
        amounts = [1000, 10000, 100000]
        probabilities = [0.95, 0.85, 0.65]
        confidence_intervals = [(0.90, 1.0), (0.80, 0.90), (0.60, 0.70)]
        recommended_amounts = [1000, 10000]
        
        curve = ReliabilityCurve(
            amounts=amounts,
            probabilities=probabilities,
            confidence_intervals=confidence_intervals,
            recommended_amounts=recommended_amounts
        )
        
        assert curve.amounts == amounts
        assert curve.probabilities == probabilities
        assert curve.confidence_intervals == confidence_intervals
        assert curve.recommended_amounts == recommended_amounts

class TestDazFlowAnalysis:
    """Tests pour la classe DazFlowAnalysis"""
    
    def test_dazflow_analysis_creation(self):
        """Test de création d'une analyse DazFlow"""
        timestamp = datetime.utcnow()
        payment_amounts = [1000, 10000, 100000]
        success_probabilities = [0.95, 0.85, 0.65]
        
        analysis = DazFlowAnalysis(
            node_id="test_node",
            timestamp=timestamp,
            payment_amounts=payment_amounts,
            success_probabilities=success_probabilities,
            dazflow_index=0.75,
            bottleneck_channels=["channel_1", "channel_2"],
            liquidity_efficiency=0.8,
            network_centrality=0.6
        )
        
        assert analysis.node_id == "test_node"
        assert analysis.timestamp == timestamp
        assert analysis.payment_amounts == payment_amounts
        assert analysis.success_probabilities == success_probabilities
        assert analysis.dazflow_index == 0.75
        assert analysis.bottleneck_channels == ["channel_1", "channel_2"]
        assert analysis.liquidity_efficiency == 0.8
        assert analysis.network_centrality == 0.6

if __name__ == "__main__":
    pytest.main([__file__]) 