import pytest
import numpy as np
import os
from datetime import datetime
import sys
from pathlib import Path

# Ajout du répertoire racine au PYTHONPATH
root_dir = str(Path(__file__).parent.parent)
sys.path.append(root_dir)

from src.ml.evaluation.evaluator import ModelEvaluator, PerformanceMetrics
from src.ml.evaluation.metrics_storage import MetricsStorage
from src.ml.evaluation.visualization import MetricsVisualizer

class MockModel:
    def predict(self, X):
        return np.zeros(len(X))
    
    def predict_proba(self, X):
        return np.array([[0.8, 0.2] for _ in range(len(X))])

@pytest.fixture
def evaluator():
    return ModelEvaluator(n_splits=2, random_state=42)

@pytest.fixture
def mock_data():
    X = np.random.rand(100, 10)
    y = np.random.randint(0, 2, 100)
    return X, y

@pytest.fixture
def mock_model():
    return MockModel()

@pytest.fixture
def metrics_storage():
    return MetricsStorage(os.getenv("MONGODB_URI"), "dazlng")

@pytest.fixture
def visualizer():
    return MetricsVisualizer("test_plots")

def test_evaluate_fold(evaluator, mock_model, mock_data):
    X, y = mock_data
    X_train, X_val = X[:80], X[80:]
    y_train, y_val = y[:80], y[80:]
    
    metrics = evaluator.evaluate_fold(mock_model, X_train, X_val, y_train, y_val)
    
    assert isinstance(metrics, PerformanceMetrics)
    assert hasattr(metrics, 'accuracy')
    assert hasattr(metrics, 'recall')
    assert hasattr(metrics, 'f1_score')
    assert hasattr(metrics, 'inference_time')
    assert hasattr(metrics, 'confusion_matrix')
    assert hasattr(metrics, 'roc_auc')
    assert hasattr(metrics, 'domain_metrics')

def test_cross_validate(evaluator, mock_model, mock_data):
    X, y = mock_data
    results = evaluator.cross_validate(mock_model, X, y)
    
    assert isinstance(results, dict)
    assert 'accuracy' in results
    assert 'recall' in results
    assert 'f1_score' in results
    assert 'inference_time' in results
    assert 'roc_auc' in results
    
    for metric in results.values():
        assert 'mean' in metric
        assert 'std' in metric

def test_metrics_storage(metrics_storage):
    run_id = f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    model_version = "1.0.0"
    metrics = {
        'accuracy': {'mean': 0.85, 'std': 0.02},
        'recall': {'mean': 0.83, 'std': 0.03}
    }
    hyperparameters = {'learning_rate': 0.01, 'batch_size': 32}
    
    # Test de sauvegarde
    success = metrics_storage.save_metrics(run_id, model_version, metrics, hyperparameters)
    assert success
    
    # Test de récupération
    history = metrics_storage.get_metrics_history(model_version)
    assert len(history) > 0
    
    latest = metrics_storage.get_latest_metrics(model_version)
    assert latest is not None
    assert latest['run_id'] == run_id
    
    # Test de suppression
    deleted = metrics_storage.delete_metrics(run_id)
    assert deleted

def test_visualization(visualizer):
    """Test des fonctionnalités de visualisation"""
    # Création du répertoire de sortie
    os.makedirs(visualizer.output_dir, exist_ok=True)
    
    # Test des courbes d'apprentissage
    train_scores = [0.7, 0.8, 0.85, 0.87, 0.89]
    val_scores = [0.65, 0.75, 0.82, 0.84, 0.86]
    visualizer.plot_learning_curves(train_scores, val_scores, "accuracy")
    
    # Vérification de l'existence du répertoire
    assert os.path.exists(visualizer.output_dir)
    
    # Nettoyage
    import shutil
    shutil.rmtree(visualizer.output_dir) 