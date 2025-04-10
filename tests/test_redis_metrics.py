import pytest
import numpy as np
from datetime import datetime
from src.ml.storage.redis_metrics import RedisMetricsStorage
from src.ml.training.metrics import MetricCollection, Accuracy, Precision, Recall, F1Score

@pytest.fixture
def redis_storage():
    """Fixture pour créer une instance de RedisMetricsStorage"""
    storage = RedisMetricsStorage(
        host="localhost",
        port=6379,
        db=15,  # Utiliser une base de données différente pour les tests
        prefix="test_metrics:"
    )
    yield storage
    # Nettoyage après les tests
    for key in storage.redis_client.keys("test_metrics:*"):
        storage.redis_client.delete(key)

def test_save_and_load_metrics(redis_storage):
    """Test de sauvegarde et chargement des métriques"""
    run_id = "test_run_1"
    metrics = {
        "accuracy": [0.8, 0.85, 0.9],
        "loss": [0.5, 0.4, 0.3]
    }
    metadata = {
        "model_type": "NeuralNetwork",
        "start_time": datetime.now().isoformat()
    }
    
    # Sauvegarder les métriques
    redis_storage.save_metrics(run_id, metrics, metadata)
    
    # Charger les métriques
    loaded_metrics = redis_storage.load_metrics(run_id)
    loaded_metadata = redis_storage.load_metadata(run_id)
    
    # Vérifier les métriques
    assert loaded_metrics == metrics
    assert loaded_metadata == metadata

def test_list_runs(redis_storage):
    """Test de la liste des runs"""
    # Créer plusieurs runs
    runs = ["run1", "run2", "run3"]
    for run_id in runs:
        redis_storage.save_metrics(run_id, {"accuracy": [0.8]})
    
    # Lister les runs
    listed_runs = redis_storage.list_runs()
    
    # Vérifier que tous les runs sont listés
    assert set(listed_runs) == set(runs)

def test_delete_run(redis_storage):
    """Test de suppression d'un run"""
    run_id = "test_delete_run"
    redis_storage.save_metrics(run_id, {"accuracy": [0.8]})
    
    # Supprimer le run
    redis_storage.delete_run(run_id)
    
    # Vérifier que le run a été supprimé
    assert redis_storage.load_metrics(run_id) == {}
    assert redis_storage.load_metadata(run_id) == {}

def test_integration_with_metric_collection(redis_storage):
    """Test d'intégration avec MetricCollection"""
    # Créer une collection de métriques
    metrics = MetricCollection([
        Accuracy(),
        Precision(),
        Recall(),
        F1Score()
    ])
    
    # Générer des prédictions et cibles de test
    predictions = np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1]])
    targets = np.array([[1, 0], [0, 1], [1, 0]])
    
    # Mettre à jour les métriques
    metric_values = metrics.update(predictions, targets)
    
    # Sauvegarder dans Redis
    run_id = "test_metric_collection"
    redis_storage.save_metrics(run_id, metric_values)
    
    # Charger depuis Redis
    loaded_metrics = redis_storage.load_metrics(run_id)
    
    # Vérifier que les métriques ont été correctement sauvegardées
    assert set(loaded_metrics.keys()) == set(metric_values.keys())
    for metric_name, values in metric_values.items():
        assert loaded_metrics[metric_name] == values 