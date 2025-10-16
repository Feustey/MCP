#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique de liquidité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.liquidity import calculate_liquidity_score


def test_calculate_liquidity_score_balanced():
    """Test avec une liquidité équilibrée (50/50)."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 5_000_000,  # 5M sats
        "remote_balance": 5_000_000,  # 5M sats
        "capacity": 10_000_000  # 10M sats
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait être très élevé pour équilibre parfait
    assert score >= 80, f"Score trop bas pour liquidité équilibrée: {score}"
    assert score <= 100, f"Score trop haut: {score}"


def test_calculate_liquidity_score_local_heavy():
    """Test avec trop de liquidité locale (déséquilibre)."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 9_000_000,  # 90% local
        "remote_balance": 1_000_000,  # 10% remote
        "capacity": 10_000_000
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait être pénalisé pour déséquilibre
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour déséquilibre: {score}"


def test_calculate_liquidity_score_remote_heavy():
    """Test avec trop de liquidité remote (déséquilibre inverse)."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 1_000_000,  # 10% local
        "remote_balance": 9_000_000,  # 90% remote
        "capacity": 10_000_000
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait aussi être pénalisé
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour déséquilibre inverse: {score}"


def test_calculate_liquidity_score_empty():
    """Test avec canal vide (0 local)."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 0,
        "remote_balance": 10_000_000,
        "capacity": 10_000_000
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait être très bas
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 20, f"Score trop élevé pour canal vide: {score}"


def test_calculate_liquidity_score_high_capacity():
    """Test avec haute capacité (bonus)."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 50_000_000,  # 50M sats
        "remote_balance": 50_000_000,  # 50M sats
        "capacity": 100_000_000  # 100M sats (haute capacité)
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait bénéficier du bonus capacité
    assert score >= 85, f"Score trop bas pour haute capacité équilibrée: {score}"
    assert score <= 100, f"Score trop haut: {score}"


def test_calculate_liquidity_score_low_capacity():
    """Test avec basse capacité."""
    channel = {
        "channel_id": "test_123",
        "local_balance": 500_000,  # 0.5M sats
        "remote_balance": 500_000,  # 0.5M sats
        "capacity": 1_000_000  # 1M sats (basse capacité)
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_liquidity_score(channel, node_data)
    
    # Score devrait être pénalisé malgré l'équilibre
    assert score >= 50, f"Score trop bas: {score}"
    assert score <= 80, f"Score trop élevé pour basse capacité: {score}"


def test_calculate_liquidity_score_bounds():
    """Test des limites (0-100)."""
    # Tester plusieurs scénarios
    test_cases = [
        {"local": 0, "remote": 10_000_000, "capacity": 10_000_000},
        {"local": 10_000_000, "remote": 0, "capacity": 10_000_000},
        {"local": 5_000_000, "remote": 5_000_000, "capacity": 10_000_000},
        {"local": 3_000_000, "remote": 7_000_000, "capacity": 10_000_000},
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "local_balance": case["local"],
            "remote_balance": case["remote"],
            "capacity": case["capacity"]
        }
        
        node_data = {"node_id": "test_node"}
        score = calculate_liquidity_score(channel, node_data)
        
        # Tous les scores doivent rester dans les limites
        assert 0 <= score <= 100, f"Score hors limites pour {case}: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

