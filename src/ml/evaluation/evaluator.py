from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.metrics import accuracy_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from sklearn.model_selection import KFold, StratifiedKFold
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    def __init__(self):
        self.accuracy: float = 0.0
        self.recall: float = 0.0
        self.f1_score: float = 0.0
        self.inference_time: float = 0.0
        self.confusion_matrix: Dict[str, List[int]] = {}
        self.roc_auc: float = 0.0
        self.domain_metrics: Dict[str, float] = {}

class ModelEvaluator:
    def __init__(self, n_splits: int = 5, random_state: int = 42):
        self.n_splits = n_splits
        self.random_state = random_state
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_fold = 0
        
    def evaluate_fold(self, model, X_train: np.ndarray, X_val: np.ndarray, 
                     y_train: np.ndarray, y_val: np.ndarray) -> PerformanceMetrics:
        """
        Évalue le modèle sur un fold spécifique
        """
        metrics = PerformanceMetrics()
        
        # Mesure du temps d'inférence
        start_time = time.time()
        y_pred = model.predict(X_val)
        metrics.inference_time = time.time() - start_time
        
        # Calcul des métriques standard
        metrics.accuracy = accuracy_score(y_val, y_pred)
        metrics.recall = recall_score(y_val, y_pred, average='weighted')
        metrics.f1_score = f1_score(y_val, y_pred, average='weighted')
        
        # Matrice de confusion
        cm = confusion_matrix(y_val, y_pred)
        metrics.confusion_matrix = {
            'true_negatives': cm[0][0],
            'false_positives': cm[0][1],
            'false_negatives': cm[1][0],
            'true_positives': cm[1][1]
        }
        
        # ROC AUC si applicable
        try:
            y_pred_proba = model.predict_proba(X_val)[:, 1]
            metrics.roc_auc = roc_auc_score(y_val, y_pred_proba)
        except:
            logger.warning("Impossible de calculer ROC AUC")
        
        # Métriques spécifiques au domaine
        metrics.domain_metrics = self._calculate_domain_metrics(model, X_val, y_val)
        
        self.metrics_history.append(metrics)
        return metrics
    
    def cross_validate(self, model, X: np.ndarray, y: np.ndarray) -> Dict:
        """
        Effectue la validation croisée sur l'ensemble des données
        """
        kf = StratifiedKFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state)
        fold_metrics = []
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X, y)):
            self.current_fold = fold
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            fold_metric = self.evaluate_fold(model, X_train, X_val, y_train, y_val)
            fold_metrics.append(fold_metric)
            
        return self._aggregate_metrics(fold_metrics)
    
    def _calculate_domain_metrics(self, model, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Calcule les métriques spécifiques au domaine
        """
        # À personnaliser selon les besoins spécifiques
        return {
            'channel_recommendation_success': 0.0,
            'average_transaction_latency': 0.0,
            'route_failure_rate': 0.0
        }
    
    def _aggregate_metrics(self, fold_metrics: List[PerformanceMetrics]) -> Dict:
        """
        Agrège les métriques de tous les folds
        """
        aggregated = {
            'accuracy': {
                'mean': np.mean([m.accuracy for m in fold_metrics]),
                'std': np.std([m.accuracy for m in fold_metrics])
            },
            'recall': {
                'mean': np.mean([m.recall for m in fold_metrics]),
                'std': np.std([m.recall for m in fold_metrics])
            },
            'f1_score': {
                'mean': np.mean([m.f1_score for m in fold_metrics]),
                'std': np.std([m.f1_score for m in fold_metrics])
            },
            'inference_time': {
                'mean': np.mean([m.inference_time for m in fold_metrics]),
                'std': np.std([m.inference_time for m in fold_metrics])
            },
            'roc_auc': {
                'mean': np.mean([m.roc_auc for m in fold_metrics]),
                'std': np.std([m.roc_auc for m in fold_metrics])
            }
        }
        
        return aggregated 