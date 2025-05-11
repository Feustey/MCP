import pytest
from src.optimizers.scoring_utils import evaluate_channel

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

def test_evaluate_channel_increase_fees():
    decision = evaluate_channel(channel_data_underperforming)
    assert decision == "INCREASE_FEES"

def test_evaluate_channel_lower_fees():
    decision = evaluate_channel(channel_data_overperforming)
    assert decision == "LOWER_FEES"

def test_evaluate_channel_no_action():
    decision = evaluate_channel(channel_data_stable)
    assert decision == "NO_ACTION"

def test_evaluate_channel_close_channel():
    decision = evaluate_channel(channel_data_to_close)
    assert decision == "CLOSE_CHANNEL" 