#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de fiabilité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.reliability import calculate_reliability_score


def test_calculate_reliability_score_high():
    """Test avec haute fiabilité."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03abc...",
        "uptime": 0.99,  # 99% uptime
        "last_update_timestamp": 1234567890
    }
    
    node_data = {"node_id": "test_node"}
    
    # Stats réseau avec uptime du pair
    network_stats = {
        "node_uptimes": {
            "03abc...": 0.98  # Bon uptime
        }
    }
    
    score = calculate_reliability_score(channel, node_data, network_stats)
    
    assert score >= 70, f"Score trop bas pour haute fiabilité: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_reliability_score_low():
    """Test avec faible fiabilité."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03def...",
        "uptime": 0.50,  # 50% uptime seulement
        "last_update_timestamp": 1234567890
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "node_uptimes": {
            "03def...": 0.60  # Uptime médiocre
        }
    }
    
    score = calculate_reliability_score(channel, node_data, network_stats)
    
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour faible fiabilité: {score}"


def test_calculate_reliability_score_no_stats():
    """Test sans statistiques."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03xyz..."
    }
    
    node_data = {"node_id": "test_node"}
    network_stats = {}
    
    score = calculate_reliability_score(channel, node_data, network_stats)
    
    # Fallback
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_reliability_score_bounds():
    """Test des limites."""
    test_cases = [
        {"uptime": 0.0, "peer_uptime": 0.0},
        {"uptime": 1.0, "peer_uptime": 1.0},
        {"uptime": 0.5, "peer_uptime": 0.7},
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "peer_node_id": "03test...",
            "uptime": case["uptime"]
        }
        
        node_data = {"node_id": "test_node"}
        network_stats = {
            "node_uptimes": {
                "03test...": case["peer_uptime"]
            }
        }
        
        score = calculate_reliability_score(channel, node_data, network_stats)
        
        assert 0 <= score <= 100, f"Score hors limites: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

