#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique d'activité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.activity import calculate_activity_score


def test_calculate_activity_score_high_activity():
    """Test avec haute activité (nombreux forwards)."""
    channel = {
        "channel_id": "test_123",
        "forwarding_history": {
            "total_forwards": 100,
            "total_volume_msat": 500_000_000,  # 500k sats
            "success_rate": 0.95  # 95% success
        }
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_activity_score(channel, node_data)
    
    assert score >= 70, f"Score trop bas pour haute activité: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_activity_score_no_activity():
    """Test sans activité."""
    channel = {
        "channel_id": "test_123",
        "forwarding_history": {
            "total_forwards": 0,
            "total_volume_msat": 0,
            "success_rate": 0
        }
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_activity_score(channel, node_data)
    
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 30, f"Score trop élevé sans activité: {score}"


def test_calculate_activity_score_low_success_rate():
    """Test avec bas taux de succès."""
    channel = {
        "channel_id": "test_123",
        "forwarding_history": {
            "total_forwards": 50,
            "total_volume_msat": 100_000_000,
            "success_rate": 0.30  # 30% seulement
        }
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_activity_score(channel, node_data)
    
    # Devrait être pénalisé pour bas taux de succès
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour bas success rate: {score}"


def test_calculate_activity_score_missing_history():
    """Test sans historique de forwarding."""
    channel = {
        "channel_id": "test_123"
        # Pas de forwarding_history
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_activity_score(channel, node_data)
    
    # Devrait utiliser valeur par défaut (médiane)
    assert score >= 20, f"Score fallback trop bas: {score}"
    assert score <= 60, f"Score fallback trop haut: {score}"


def test_calculate_activity_score_bounds():
    """Test des limites."""
    test_cases = [
        {"forwards": 0, "volume": 0, "success": 0},
        {"forwards": 1000, "volume": 1_000_000_000, "success": 1.0},
        {"forwards": 50, "volume": 100_000_000, "success": 0.5},
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "forwarding_history": {
                "total_forwards": case["forwards"],
                "total_volume_msat": case["volume"],
                "success_rate": case["success"]
            }
        }
        
        node_data = {"node_id": "test_node"}
        score = calculate_activity_score(channel, node_data)
        
        assert 0 <= score <= 100, f"Score hors limites: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

