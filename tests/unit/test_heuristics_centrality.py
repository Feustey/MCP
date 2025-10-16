#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de centralité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.centrality import calculate_centrality_score


def test_calculate_centrality_score_high():
    """Test avec une haute centralité (nœud hub)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03abc..."
    }
    
    node_data = {
        "node_id": "test_node",
        "channels": [channel]
    }
    
    network_graph = {}  # Graphe vide, utilise fallback
    
    # Simula stats avec haute centralité
    network_stats = {
        "centrality_scores": {
            "03abc...": 0.8  # Haute centralité
        }
    }
    
    score = calculate_centrality_score(channel, node_data, network_graph, network_stats)
    
    # Score devrait être élevé (proche de 100)
    assert score >= 60, f"Score trop bas pour haute centralité: {score}"
    assert score <= 100, f"Score trop haut: {score}"


def test_calculate_centrality_score_low():
    """Test avec une basse centralité (nœud périphérique)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03def..."
    }
    
    node_data = {
        "node_id": "test_node",
        "channels": [channel]
    }
    
    network_graph = {}
    
    # Basse centralité
    network_stats = {
        "centrality_scores": {
            "03def...": 0.1  # Basse centralité
        }
    }
    
    score = calculate_centrality_score(channel, node_data, network_graph, network_stats)
    
    # Score devrait être bas
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 30, f"Score trop élevé pour basse centralité: {score}"


def test_calculate_centrality_score_no_stats():
    """Test sans statistiques réseau (fallback)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03xyz..."
    }
    
    node_data = {
        "node_id": "test_node",
        "channels": [channel]
    }
    
    network_graph = {}
    network_stats = {}  # Pas de stats
    
    score = calculate_centrality_score(channel, node_data, network_graph, network_stats)
    
    # Score devrait utiliser fallback (médian, ~50)
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_centrality_score_bounds():
    """Test des limites (0-100)."""
    channel = {
        "channel_id": "test_123",
        "peer_node_id": "03test..."
    }
    
    node_data = {
        "node_id": "test_node",
        "channels": [channel]
    }
    
    network_graph = {}
    
    # Centralité extrême
    network_stats = {
        "centrality_scores": {
            "03test...": 1.0  # Maximum
        }
    }
    
    score = calculate_centrality_score(channel, node_data, network_graph, network_stats)
    
    # Doit rester dans les limites
    assert 0 <= score <= 100, f"Score hors limites: {score}"


def test_calculate_centrality_score_multiple_channels():
    """Test avec un nœud ayant plusieurs canaux."""
    channel1 = {
        "channel_id": "test_123",
        "peer_node_id": "03peer1..."
    }
    
    channel2 = {
        "channel_id": "test_456",
        "peer_node_id": "03peer2..."
    }
    
    node_data = {
        "node_id": "test_node",
        "channels": [channel1, channel2]
    }
    
    network_graph = {}
    network_stats = {
        "centrality_scores": {
            "03peer1...": 0.6,
            "03peer2...": 0.4
        }
    }
    
    score1 = calculate_centrality_score(channel1, node_data, network_graph, network_stats)
    score2 = calculate_centrality_score(channel2, node_data, network_graph, network_stats)
    
    # Le canal vers le nœud plus central devrait avoir un meilleur score
    assert score1 > score2, "Le canal vers le nœud plus central devrait avoir un meilleur score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

