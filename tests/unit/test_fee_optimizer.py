import pytest
from unittest.mock import patch, MagicMock
from src.optimizers.feustey_fee_optimizer import optimize_fees, calculate_optimal_fee, apply_fee_changes

# Données de test
test_channel_data = {
    "channel_id": "123x456x0",
    "capacity": 5000000,
    "local_balance": 2500000,
    "remote_balance": 2500000,
    "uptime": 0.98,
    "num_updates": 150,
    "current_base_fee": 1000,
    "current_fee_rate": 1,
    "score": 0.85,
    "peer_node": {
        "node_id": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "alias": "ACINQ",
        "num_channels": 100
    }
}

test_channel_data_low_score = {
    **test_channel_data,
    "score": 0.3
}

test_network_data = {
    "average_base_fee": 1500,
    "average_fee_rate": 2.5,
    "median_base_fee": 1200,
    "median_fee_rate": 2.0,
    "p90_base_fee": 3000,
    "p90_fee_rate": 5.0
}

@pytest.fixture
def mock_api_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "success": True,
        "channel_id": "123x456x0",
        "old_base_fee": 1000,
        "old_fee_rate": 1,
        "new_base_fee": 1200,
        "new_fee_rate": 2
    }
    mock_resp.status_code = 200
    return mock_resp

def test_calculate_optimal_fee():
    """Test du calcul des frais optimaux pour un canal à score élevé."""
    result = calculate_optimal_fee(test_channel_data, test_network_data)
    
    # Pour un canal avec un bon score, les frais devraient être légèrement supérieurs à la médiane
    assert result["base_fee"] > test_network_data["median_base_fee"]
    assert result["base_fee"] < test_network_data["p90_base_fee"]
    assert result["fee_rate"] > test_network_data["median_fee_rate"]
    assert result["fee_rate"] < test_network_data["p90_fee_rate"]

def test_calculate_optimal_fee_low_score():
    """Test du calcul des frais optimaux pour un canal à score faible."""
    result = calculate_optimal_fee(test_channel_data_low_score, test_network_data)
    
    # Pour un canal avec un mauvais score, les frais devraient être plus agressifs
    assert result["base_fee"] > test_network_data["p90_base_fee"]
    assert result["fee_rate"] > test_network_data["p90_fee_rate"]

@patch('src.optimizers.feustey_fee_optimizer.requests.post')
def test_apply_fee_changes_success(mock_post, mock_api_response):
    """Test de l'application des changements de frais avec succès."""
    mock_post.return_value = mock_api_response
    
    changes = {
        "channel_id": "123x456x0",
        "new_base_fee": 1200,
        "new_fee_rate": 2
    }
    
    result = apply_fee_changes(changes)
    assert result["success"] is True
    assert result["channel_id"] == "123x456x0"
    assert result["new_base_fee"] == 1200
    assert result["new_fee_rate"] == 2

@patch('src.optimizers.feustey_fee_optimizer.requests.post')
def test_apply_fee_changes_failure(mock_post):
    """Test de l'application des changements de frais avec échec."""
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {"error": "API error"}
    
    changes = {
        "channel_id": "123x456x0",
        "new_base_fee": 1200,
        "new_fee_rate": 2
    }
    
    result = apply_fee_changes(changes)
    assert result["success"] is False
    assert "error" in result

@patch('src.optimizers.feustey_fee_optimizer.calculate_optimal_fee')
@patch('src.optimizers.feustey_fee_optimizer.apply_fee_changes')
def test_optimize_fees(mock_apply_fee_changes, mock_calculate_optimal_fee):
    """Test de l'optimisation complète des frais pour plusieurs canaux."""
    # Configuration des mocks
    mock_calculate_optimal_fee.return_value = {
        "base_fee": 1200,
        "fee_rate": 2
    }
    mock_apply_fee_changes.return_value = {
        "success": True,
        "channel_id": "123x456x0"
    }
    
    # Données de test
    channels = [test_channel_data, test_channel_data_low_score]
    
    # Appel de la fonction à tester
    results = optimize_fees(channels, test_network_data)
    
    # Vérifications
    assert len(results) == 2
    assert mock_calculate_optimal_fee.call_count == 2
    assert mock_apply_fee_changes.call_count == 2
    
    for result in results:
        assert result["success"] is True 