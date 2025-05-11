import pytest
# from src.optimizers.scoring_utils import calculate_channel_score, calculate_node_score, normalize_scores
from app.models import LightningChannel

# from src.optimizers.scoring import evaluate_channel

channel_data_underperforming = {
    "id": "123x456x0",
    "capacity": 1_000_000,
    "local_balance": 100_000,
    "remote_balance": 900_000,
    "uptime": 0.85,
    "age_days": 120,
    "forward_count": 2,
    "base_fee": 1000,
    "fee_rate": 1,
    "centrality": 0.1,
    "volume_24h": 10_000,
    "volume_48h": 15_000,
    "status": "active"
}

channel_data_overperforming = {
    "id": "789x123x1",
    "capacity": 2_000_000,
    "local_balance": 1_500_000,
    "remote_balance": 500_000,
    "uptime": 0.99,
    "age_days": 300,
    "forward_count": 50,
    "base_fee": 1000,
    "fee_rate": 1,
    "centrality": 0.8,
    "volume_24h": 500_000,
    "volume_48h": 900_000,
    "status": "active"
}

channel_data_stable = {
    "id": "456x789x2",
    "capacity": 1_500_000,
    "local_balance": 750_000,
    "remote_balance": 750_000,
    "uptime": 0.97,
    "age_days": 200,
    "forward_count": 20,
    "base_fee": 1000,
    "fee_rate": 1,
    "centrality": 0.5,
    "volume_24h": 100_000,
    "volume_48h": 200_000,
    "status": "active"
}

channel_data_to_close = {
    "id": "321x654x3",
    "capacity": 500_000,
    "local_balance": 0,
    "remote_balance": 500_000,
    "uptime": 0.2,
    "age_days": 10,
    "forward_count": 0,
    "base_fee": 1000,
    "fee_rate": 1,
    "centrality": 0.01,
    "volume_24h": 0,
    "volume_48h": 0,
    "status": "inactive"
}

# Les tests suivants sont désactivés car evaluate_channel n'existe pas dans scoring_utils
# def test_evaluate_channel_increase_fees():
#     decision = evaluate_channel(channel_data_underperforming)
#     assert decision == "INCREASE_FEES"
#
# def test_evaluate_channel_lower_fees():
#     decision = evaluate_channel(channel_data_overperforming)
#     assert decision == "LOWER_FEES"
#
# def test_evaluate_channel_no_action():
#     decision = evaluate_channel(channel_data_stable)
#     assert decision == "NO_ACTION"
#
# def test_evaluate_channel_close_channel():
#     decision = evaluate_channel(channel_data_to_close)
#     assert decision == "CLOSE_CHANNEL"

@pytest.mark.parametrize("channel_data, expected_score", [
    # Cas nominal avec bonnes valeurs
    (
        {
            "capacity": 5000000,
            "local_balance": 2500000,
            "remote_balance": 2500000,
            "uptime": 0.98,
            "num_updates": 150,
            "age": 500
        }, 
        0.85
    ),
    # Canal déséquilibré
    (
        {
            "capacity": 5000000,
            "local_balance": 4500000,
            "remote_balance": 500000,
            "uptime": 0.98,
            "num_updates": 150,
            "age": 500
        }, 
        0.65
    ),
    # Canal peu utilisé
    (
        {
            "capacity": 5000000,
            "local_balance": 2500000,
            "remote_balance": 2500000,
            "uptime": 0.98,
            "num_updates": 5,
            "age": 500
        }, 
        0.55
    ),
])
def test_calculate_channel_score(channel_data, expected_score):
    """Test du calcul de score pour un canal."""
    score = calculate_channel_score(channel_data)
    assert abs(score - expected_score) < 0.1  # Tolérance de 0.1 pour les calculs de score

@pytest.mark.parametrize("node_data, expected_score", [
    # Nœud avec bonne connectivité
    (
        {
            "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
            "alias": "ACINQ",
            "num_channels": 100,
            "total_capacity": 50000000,
            "betweenness_centrality": 0.05,
            "uptime": 0.99
        }, 
        0.9
    ),
    # Nœud avec mauvaise connectivité
    (
        {
            "node_id": "abc123",
            "alias": "SmallNode",
            "num_channels": 5,
            "total_capacity": 1000000,
            "betweenness_centrality": 0.001,
            "uptime": 0.7
        }, 
        0.3
    ),
])
def test_calculate_node_score(node_data, expected_score):
    """Test du calcul de score pour un nœud."""
    score = calculate_node_score(node_data)
    assert abs(score - expected_score) < 0.1  # Tolérance de 0.1 pour les calculs de score

def test_normalize_scores():
    """Test de la normalisation des scores."""
    raw_scores = {
        "channel1": 85,
        "channel2": 20,
        "channel3": 50
    }
    
    normalized = normalize_scores(raw_scores)
    
    # Vérification des limites
    assert max(normalized.values()) <= 1.0
    assert min(normalized.values()) >= 0.0
    
    # Vérification de l'ordre relatif
    assert normalized["channel1"] > normalized["channel3"] > normalized["channel2"] 

def test_lightning_channel_fee_rate_validation():
    # Teste qu'une ValueError est levée si fee_rate < 0
    with pytest.raises(ValueError):
        LightningChannel(
            id="chan1",
            node1_pub="pub1",
            node2_pub="pub2",
            capacity=1000000,
            last_update="2023-10-27T10:00:00Z",
            status="active",
            fee_rate=-1
        )
    # Teste qu'une ValueError est levée si fee_rate > 10000
    with pytest.raises(ValueError):
        LightningChannel(
            id="chan2",
            node1_pub="pub1",
            node2_pub="pub2",
            capacity=1000000,
            last_update="2023-10-27T10:00:00Z",
            status="active",
            fee_rate=10001
        )
    # Teste qu'aucune erreur n'est levée pour une valeur valide
    LightningChannel(
        id="chan3",
        node1_pub="pub1",
        node2_pub="pub2",
        capacity=1000000,
        last_update="2023-10-27T10:00:00Z",
        status="active",
        fee_rate=5000
    ) 