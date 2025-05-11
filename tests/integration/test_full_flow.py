import pytest
from src.optimizers.parsing_amboss_utils import parse_amboss_data
from src.optimizers.scoring_utils import evaluate_channel
from src.optimizers.fee_update_utils import update_fee_policy
from src.optimizers.error_handling_utils import handle_error

# Exemples de données pour le test d'intégration
amboss_data_valid = {
    "channels": [
        {
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
    ]
}

amboss_data_underperforming = {
    "channels": [
        {
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
    ]
}

amboss_data_overperforming = {
    "channels": [
        {
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
    ]
}

amboss_data_to_close = {
    "channels": [
        {
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
    ]
}

fee_update_request = {
    "channel_id": "123x456x0",
    "new_base_fee": 1200,
    "new_fee_rate": 2
}

def test_full_decision_flow():
    # Cas sous-performant (INCREASE_FEES)
    parsed = parse_amboss_data(amboss_data_underperforming)
    channel = parsed["channels"][0]
    decision = evaluate_channel(channel)
    if decision == "INCREASE_FEES":
        result = update_fee_policy(fee_update_request)
        assert result["success"] is True
    else:
        assert decision in ["NO_ACTION", "LOWER_FEES", "CLOSE_CHANNEL"]
    assert handle_error(channel) == "OK"

    # Cas sur-performant (LOWER_FEES)
    parsed = parse_amboss_data(amboss_data_overperforming)
    channel = parsed["channels"][0]
    decision = evaluate_channel(channel)
    assert decision == "LOWER_FEES"
    assert handle_error(channel) == "OK"

    # Cas à fermer (CLOSE_CHANNEL)
    parsed = parse_amboss_data(amboss_data_to_close)
    channel = parsed["channels"][0]
    decision = evaluate_channel(channel)
    assert decision == "CLOSE_CHANNEL"
    assert handle_error(channel) == "OK"

def test_system_response_to_corrupted_input():
    # Parsing Amboss avec données corrompues
    with pytest.raises(ValueError):
        parse_amboss_data("NOT_A_JSON")
    # Gestion d'erreur sur données corrompues
    with pytest.raises(ValueError):
        handle_error("NOT_A_JSON") 