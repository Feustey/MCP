import pytest
from src.optimizers.error_handling_utils import handle_error

# from src.core.error_handling import handle_error

data_corrupted = "NOT_A_JSON"
data_missing = {}
data_aberrant = {"id": None, "capacity": -1000, "status": "unknown"}

def test_handle_corrupted_data():
    with pytest.raises(ValueError):
        handle_error(data_corrupted)

def test_handle_missing_data():
    with pytest.raises(KeyError):
        handle_error(data_missing)

def test_handle_aberrant_data():
    with pytest.raises(ValueError):
        handle_error(data_aberrant) 