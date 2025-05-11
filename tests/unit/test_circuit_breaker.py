import pytest
from unittest.mock import patch, MagicMock
import json
import os
from datetime import datetime, timedelta
from src.tools.circuit_breaker import (
    CircuitBreaker, 
    check_rollback_condition, 
    create_rollback_snapshot,
    apply_rollback
)

@pytest.fixture
def mock_redis_client():
    """Mock du client Redis."""
    mock_client = MagicMock()
    mock_client.get.return_value = None
    return mock_client

@pytest.fixture
def sample_fee_changes():
    """Exemple de changements de frais pour les tests."""
    return [
        {
            "channel_id": "123x456x0",
            "timestamp": datetime.now().isoformat(),
            "old_base_fee": 1000,
            "old_fee_rate": 1,
            "new_base_fee": 1200,
            "new_fee_rate": 2
        },
        {
            "channel_id": "789x012x0",
            "timestamp": datetime.now().isoformat(),
            "old_base_fee": 500,
            "old_fee_rate": 0.5,
            "new_base_fee": 800,
            "new_fee_rate": 1
        }
    ]

@pytest.fixture
def rollback_snapshot(sample_fee_changes, tmp_path):
    """Crée un snapshot de rollback pour les tests."""
    snapshot_dir = tmp_path / "rollbacks"
    snapshot_dir.mkdir(exist_ok=True)
    
    snapshot_file = snapshot_dir / f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(sample_fee_changes, f)
    
    return str(snapshot_file)

class TestCircuitBreaker:
    
    def test_init(self, mock_redis_client):
        """Test de l'initialisation du circuit breaker."""
        cb = CircuitBreaker(redis_client=mock_redis_client, failure_threshold=3, reset_timeout=300)
        
        assert cb.failure_count == 0
        assert cb.failure_threshold == 3
        assert cb.reset_timeout == 300
        assert cb.redis_client == mock_redis_client
        assert cb.is_open() is False
    
    def test_record_failure(self, mock_redis_client):
        """Test d'enregistrement d'un échec."""
        cb = CircuitBreaker(redis_client=mock_redis_client, failure_threshold=3)
        
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.is_open() is False
        
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 3
        assert cb.is_open() is True
    
    def test_reset(self, mock_redis_client):
        """Test de réinitialisation du circuit breaker."""
        cb = CircuitBreaker(redis_client=mock_redis_client, failure_threshold=3)
        
        cb.failure_count = 3
        cb.last_failure_time = datetime.now() - timedelta(minutes=10)
        
        cb.reset()
        assert cb.failure_count == 0
        assert cb.is_open() is False
    
    @patch('src.tools.circuit_breaker.time.time')
    def test_auto_reset_after_timeout(self, mock_time, mock_redis_client):
        """Test de réinitialisation automatique après un délai."""
        cb = CircuitBreaker(redis_client=mock_redis_client, failure_threshold=3, reset_timeout=300)
        
        # Simuler 3 échecs
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        
        assert cb.is_open() is True
        
        # Avancer le temps de 5 minutes (300 secondes)
        current_time = time.time()
        mock_time.return_value = current_time + 301
        
        # Le circuit devrait être fermé après le délai
        assert cb.is_open() is False

def test_check_rollback_condition(mock_redis_client):
    """Test de la vérification des conditions de rollback."""
    cb = CircuitBreaker(redis_client=mock_redis_client, failure_threshold=3)
    
    # Pas de rollback quand le circuit est fermé
    result = check_rollback_condition(cb, error_rate=0.05)
    assert result is False
    
    # Forcer l'ouverture du circuit
    cb.failure_count = 5
    
    # Rollback quand le circuit est ouvert et taux d'erreur élevé
    result = check_rollback_condition(cb, error_rate=0.15)
    assert result is True
    
    # Pas de rollback si taux d'erreur faible malgré circuit ouvert
    result = check_rollback_condition(cb, error_rate=0.02)
    assert result is False

@patch('src.tools.circuit_breaker.os.path.join')
@patch('src.tools.circuit_breaker.json.dump')
def test_create_rollback_snapshot(mock_json_dump, mock_path_join, sample_fee_changes):
    """Test de la création d'un snapshot pour rollback."""
    mock_path_join.return_value = "/tmp/rollbacks/snapshot.json"
    
    snapshot_file = create_rollback_snapshot(sample_fee_changes)
    
    assert snapshot_file is not None
    assert "rollback_" in mock_path_join.call_args[0][1]
    assert mock_json_dump.called

@patch('src.tools.circuit_breaker.requests.post')
def test_apply_rollback(mock_post, rollback_snapshot):
    """Test de l'application d'un rollback."""
    # Mock de réponse API pour le rollback
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}
    
    result = apply_rollback(rollback_snapshot)
    
    assert result["success"] is True
    assert result["rollback_file"] == rollback_snapshot
    assert mock_post.call_count == 2  # Deux canaux à restaurer

@patch('src.tools.circuit_breaker.requests.post')
def test_apply_rollback_failure(mock_post, rollback_snapshot):
    """Test de l'échec d'application d'un rollback."""
    # Mock d'échec API pour le rollback
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {"error": "API error"}
    
    result = apply_rollback(rollback_snapshot)
    
    assert result["success"] is False
    assert "error" in result
    assert mock_post.called 