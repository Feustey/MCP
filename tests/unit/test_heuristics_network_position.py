#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de position réseau.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.network_position import calculate_network_position_score


def test_calculate_network_position_score_hub():
    """Test avec nœud hub (centrale)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03abc..."
    }
    
    node_data = {"node_id": "test_node"}
    
    # Stats réseau avec pair en position hub
    network_stats = {
        "node_channel_counts": {
            "03abc...": 1000  # Nombreux canaux = hub
        },
        "average_channel_count": 50,  # Médiane réseau
        "centrality_scores": {
            "03abc...": 0.85  # Haute centralité
        }
    }
    
    score = calculate_network_position_score(channel, node_data, network_stats)
    
    assert score >= 70, f"Score trop bas pour position hub: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_network_position_score_edge():
    """Test avec nœud périphérique (edge)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03def..."
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "node_channel_counts": {
            "03def...": 3  # Peu de canaux = edge
        },
        "average_channel_count": 50,
        "centrality_scores": {
            "03def...": 0.10  # Faible centralité
        }
    }
    
    score = calculate_network_position_score(channel, node_data, network_stats)
    
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 40, f"Score trop élevé pour position edge: {score}"


def test_calculate_network_position_score_average():
    """Test avec nœud en position moyenne."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03xyz..."
    }
    
    node_data = {"node_id": "test_node"}
    
    network_stats = {
        "node_channel_counts": {
            "03xyz...": 50  # Égal à la moyenne
        },
        "average_channel_count": 50,
        "centrality_scores": {
            "03xyz...": 0.50  # Centralité moyenne
        }
    }
    
    score = calculate_network_position_score(channel, node_data, network_stats)
    
    # Score médian
    assert score >= 40, f"Score trop bas pour position moyenne: {score}"
    assert score <= 70, f"Score trop élevé pour position moyenne: {score}"


def test_calculate_network_position_score_no_stats():
    """Test sans statistiques."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03test..."
    }
    
    node_data = {"node_id": "test_node"}
    network_stats = {}
    
    score = calculate_network_position_score(channel, node_data, network_stats)
    
    # Fallback
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_network_position_score_bounds():
    """Test des limites."""
    test_cases = [
        {"channels": 1, "avg": 50, "centrality": 0.0},
        {"channels": 5000, "avg": 50, "centrality": 1.0},
        {"channels": 100, "avg": 50, "centrality": 0.5},
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "peer_node_id": "03test..."
        }
        
        node_data = {"node_id": "test_node"}
        network_stats = {
            "node_channel_counts": {"03test...": case["channels"]},
            "average_channel_count": case["avg"],
            "centrality_scores": {"03test...": case["centrality"]}
        }
        
        score = calculate_network_position_score(channel, node_data, network_stats)
        
        assert 0 <= score <= 100, f"Score hors limites: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

