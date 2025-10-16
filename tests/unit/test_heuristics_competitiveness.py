#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de compétitivité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.competitiveness import calculate_competitiveness_score


def test_calculate_competitiveness_score_competitive():
    """Test avec frais compétitifs (en dessous de la médiane)."""
    channel = {
        "channel_id": "test_123",
        "policy": {
            "base_fee_msat": 1000,
            "fee_rate_ppm": 300  # Bas = compétitif
        }
    }
    
    node_data = {"node_id": "test_node"}
    
    # Stats réseau avec médiane plus élevée
    network_stats = {
        "median_base_fee": 1500,
        "median_fee_rate": 500
    }
    
    score = calculate_competitiveness_score(channel, node_data, network_stats)
    
    assert score >= 60, f"Score trop bas pour frais compétitifs: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_competitiveness_score_expensive():
    """Test avec frais élevés (au-dessus de la médiane)."""
    channel = {
        "channel_id": "test_123",
        "policy": {
            "base_fee_msat": 3000,
            "fee_rate_ppm": 1000  # Élevé = non compétitif
        }
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "median_base_fee": 1000,
        "median_fee_rate": 500
    }
    
    score = calculate_competitiveness_score(channel, node_data, network_stats)
    
    # Devrait être pénalisé
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour frais élevés: {score}"


def test_calculate_competitiveness_score_no_stats():
    """Test sans statistiques réseau."""
    channel = {
        "channel_id": "test_123",
        "policy": {
            "base_fee_msat": 1000,
            "fee_rate_ppm": 500
        }
    }
    
    node_data = {"node_id": "test_node"}
    network_stats = {}  # Pas de stats
    
    score = calculate_competitiveness_score(channel, node_data, network_stats)
    
    # Devrait utiliser fallback
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_competitiveness_score_bounds():
    """Test des limites."""
    test_cases = [
        {"base": 0, "rate": 0},  # Gratuit (très compétitif)
        {"base": 10000, "rate": 5000},  # Très cher
        {"base": 1000, "rate": 500},  # Normal
    ]
    
    network_stats = {
        "median_base_fee": 1000,
        "median_fee_rate": 500
    }
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "policy": {
                "base_fee_msat": case["base"],
                "fee_rate_ppm": case["rate"]
            }
        }
        
        node_data = {"node_id": "test_node"}
        score = calculate_competitiveness_score(channel, node_data, network_stats)
        
        assert 0 <= score <= 100, f"Score hors limites pour {case}: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

