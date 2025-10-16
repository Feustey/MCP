#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de qualité du pair.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.peer_quality import calculate_peer_quality_score


def test_calculate_peer_quality_score_high():
    """Test avec pair de haute qualité."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03abc..."
    }
    
    node_data = {"node_id": "test_node"}
    
    # Stats réseau avec bon pair
    network_stats = {
        "node_reputations": {
            "03abc...": 0.90  # Haute réputation
        },
        "node_channel_counts": {
            "03abc...": 500  # Bien connecté
        },
        "node_uptimes": {
            "03abc...": 0.99  # Excellent uptime
        }
    }
    
    score = calculate_peer_quality_score(channel, node_data, network_stats)
    
    assert score >= 70, f"Score trop bas pour pair de qualité: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_peer_quality_score_low():
    """Test avec pair de faible qualité."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03def..."
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "node_reputations": {
            "03def...": 0.30  # Faible réputation
        },
        "node_channel_counts": {
            "03def...": 5  # Peu connecté
        },
        "node_uptimes": {
            "03def...": 0.60  # Uptime médiocre
        }
    }
    
    score = calculate_peer_quality_score(channel, node_data, network_stats)
    
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour pair de faible qualité: {score}"


def test_calculate_peer_quality_score_no_stats():
    """Test sans statistiques."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03xyz..."
    }
    
    node_data = {"node_id": "test_node"}
    network_stats = {}
    
    score = calculate_peer_quality_score(channel, node_data, network_stats)
    
    # Fallback
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_peer_quality_score_well_connected():
    """Test avec pair très bien connecté."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03hub..."
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "node_channel_counts": {
            "03hub...": 2000  # Hub majeur
        },
        "node_reputations": {
            "03hub...": 0.95
        }
    }
    
    score = calculate_peer_quality_score(channel, node_data, network_stats)
    
    # Bonus pour connectivité élevée
    assert score >= 75, f"Score trop bas pour hub majeur: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_peer_quality_score_bounds():
    """Test des limites."""
    test_cases = [
        {"reputation": 0.0, "channels": 1, "uptime": 0.0},
        {"reputation": 1.0, "channels": 5000, "uptime": 1.0},
        {"reputation": 0.5, "channels": 100, "uptime": 0.8},
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "peer_node_id": "03test..."
        }
        
        node_data = {"node_id": "test_node"}
        network_stats = {
            "node_reputations": {"03test...": case["reputation"]},
            "node_channel_counts": {"03test...": case["channels"]},
            "node_uptimes": {"03test...": case["uptime"]}
        }
        
        score = calculate_peer_quality_score(channel, node_data, network_stats)
        
        assert 0 <= score <= 100, f"Score hors limites: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

