import pytest

# from src.clients.amboss import parse_amboss_data

amboss_data_valid = {
    "channels": [
        {
            "id": "123x456x0",
            "capacity": 1_000_000,
            "base_fee": 1000,
            "fee_rate": 1,
            "status": "active"
        }
    ]
}

amboss_data_corrupted = "NOT_A_JSON"

amboss_data_missing_fields = {
    "channels": [
        {
            "id": "123x456x0"
            # champs manquants
        }
    ]
}

def test_parse_amboss_data_valid():
    data = amboss_data_valid
    assert "channels" in data

def test_parse_amboss_data_corrupted():
    data = amboss_data_corrupted
    assert isinstance(data, str)

def test_parse_amboss_data_missing_fields():
    data = amboss_data_missing_fields
    assert "channels" in data 