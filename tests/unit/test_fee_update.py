import pytest
from src.optimizers.fee_update_utils import update_fee_policy

# from src.optimizers.fee_update import update_fee_policy

fee_update_request = {
    "channel_id": "123x456x0",
    "new_base_fee": 1200,
    "new_fee_rate": 2
}

fee_update_success_response = {
    "success": True,
    "channel_id": "123x456x0",
    "old_base_fee": 1000,
    "old_fee_rate": 1,
    "new_base_fee": 1200,
    "new_fee_rate": 2
}

fee_update_failure_request = {
    "channel_id": "fail-chan-001",
    "new_base_fee": 1200,
    "new_fee_rate": 2
}

def test_update_fee_policy_success():
    data = update_fee_policy(fee_update_request)
    assert data["success"] is True
    assert data["new_base_fee"] == 1200
    assert data["new_fee_rate"] == 2

def test_update_fee_policy_failure():
    data = update_fee_policy(fee_update_failure_request)
    assert data["success"] is False
    assert data["error"] == "API unavailable" 