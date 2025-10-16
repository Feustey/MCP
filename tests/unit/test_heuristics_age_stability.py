#!/usr/bin/env python3
"""
Tests unitaires pour l'heuristique d'âge et stabilité.

Dernière mise à jour: 15 octobre 2025
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.optimizers.heuristics.age_stability import calculate_age_stability_score


def test_calculate_age_stability_score_old_stable():
    """Test avec canal ancien et stable."""
    # Canal de 1 an
    one_year_ago = int((datetime.utcnow() - timedelta(days=365)).timestamp())
    
    channel = {
        "channel_id": "test_123",
        "created_at": one_year_ago,
        "policy_changes": []  # Aucun changement récent
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_age_stability_score(channel, node_data)
    
    assert score >= 70, f"Score trop bas pour canal ancien stable: {score}"
    assert score <= 100, f"Score invalide: {score}"


def test_calculate_age_stability_score_new():
    """Test avec canal récent."""
    # Canal de 1 jour
    one_day_ago = int((datetime.utcnow() - timedelta(days=1)).timestamp())
    
    channel = {
        "channel_id": "test_123",
        "created_at": one_day_ago
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_age_stability_score(channel, node_data)
    
    # Pénalité pour canal récent
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 50, f"Score trop élevé pour canal récent: {score}"


def test_calculate_age_stability_score_unstable():
    """Test avec canal instable (nombreux changements)."""
    six_months_ago = int((datetime.utcnow() - timedelta(days=180)).timestamp())
    recent = int((datetime.utcnow() - timedelta(days=1)).timestamp())
    
    channel = {
        "channel_id": "test_123",
        "created_at": six_months_ago,
        "policy_changes": [
            {"timestamp": recent, "type": "fee_update"},
            {"timestamp": recent - 86400, "type": "fee_update"},
            {"timestamp": recent - 172800, "type": "fee_update"},
        ]  # 3 changements récents = instable
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_age_stability_score(channel, node_data)
    
    # Pénalité pour instabilité
    assert score >= 0, f"Score négatif: {score}"
    assert score <= 60, f"Score trop élevé pour instabilité: {score}"


def test_calculate_age_stability_score_missing_data():
    """Test sans données de création."""
    channel = {
        "channel_id": "test_123"
        # Pas de created_at
    }
    
    node_data = {"node_id": "test_node"}
    
    score = calculate_age_stability_score(channel, node_data)
    
    # Fallback
    assert score >= 30, f"Score fallback trop bas: {score}"
    assert score <= 70, f"Score fallback trop haut: {score}"


def test_calculate_age_stability_score_bounds():
    """Test des limites."""
    now = int(datetime.utcnow().timestamp())
    
    test_cases = [
        {"created": now - (365 * 24 * 3600), "changes": []},  # 1 an, stable
        {"created": now - (7 * 24 * 3600), "changes": []},  # 1 semaine
        {"created": now - (30 * 24 * 3600), "changes": [{"timestamp": now} for _ in range(5)]},  # 1 mois, instable
    ]
    
    for case in test_cases:
        channel = {
            "channel_id": "test_123",
            "created_at": case["created"],
            "policy_changes": case.get("changes", [])
        }
        
        node_data = {"node_id": "test_node"}
        score = calculate_age_stability_score(channel, node_data)
        
        assert 0 <= score <= 100, f"Score hors limites: {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

