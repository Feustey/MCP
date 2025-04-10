from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import time
import uuid
from datetime import datetime
from ..models.neural_net import NeuralNetwork
from ..optimizers.base import BaseOptimizer
from ..losses.base import BaseLoss
from .metrics import MetricCollection, Accuracy, Precision, Recall, F1Score, ROCAUC
from ..storage.redis_metrics import RedisMetricsStorage

class TrainingMetrics:
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            'loss': [],
            'accuracy': [],
            'learning_rate': [],
            'epoch_time': []
        }
    
    def update(self, metric_name: str, value: float):
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def get_metrics(self) -> Dict[str, List[float]]:
        return self.metrics

class Trainer:
    def __init__(
        self,
        model: NeuralNetwork,
        optimizer: BaseOptimizer,
        loss_fn: BaseLoss,
        batch_size: int = 32,
        n_epochs: int = 100,
        validation_split: float = 0.2,
        early_stopping_patience: int = 5,
        metrics: Optional[List[str]] = None,
        redis_config: Optional[Dict[str, Any]] = None
    ):
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.validation_split = validation_split
        self.early_stopping_patience = early_stopping_patience
        
        # Initialiser les métriques
        if metrics is None:
            metrics = ["accuracy"]
        
        metric_classes = {
            "accuracy": Accuracy,
            "precision": Precision,
            "recall": Recall,
            "f1": F1Score,
            "roc_auc": ROCAUC
        }
        
        self.metrics = MetricCollection([
            metric_classes[metric]() for metric in metrics
        ])
        
        self.history: Dict[str, List[float]] = {
            "train_loss": [],
            "val_loss": [],
            **{metric: [] for metric in metrics}
        }

        # Initialiser le stockage Redis si configuré
        self.redis_storage = None
        if redis_config:
            self.redis_storage = RedisMetricsStorage(**redis_config)
            self.run_id = str(uuid.uuid4())
            self.run_metadata = {
                "start_time": datetime.now().isoformat(),
                "model_type": model.__class__.__name__,
                "optimizer_type": optimizer.__class__.__name__,
                "loss_fn_type": loss_fn.__class__.__name__,
                "batch_size": batch_size,
                "n_epochs": n_epochs,
                "validation_split": validation_split,
                "early_stopping_patience": early_stopping_patience,
                "metrics": metrics
            }
    
    def _split_data(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Divise les données en ensembles d'entraînement et de validation"""
        indices = np.random.permutation(len(X))
        split_idx = int(len(X) * (1 - self.validation_split))
        
        train_indices = indices[:split_idx]
        val_indices = indices[split_idx:]
        
        return (X[train_indices], y[train_indices],
                X[val_indices], y[val_indices])
    
    def train_step(self, X_batch: np.ndarray, y_batch: np.ndarray) -> float:
        """Étape d'entraînement"""
        # Forward pass
        predictions = self.model.forward(X_batch)
        
        # Calcul de la perte
        loss = self.loss_fn(predictions, y_batch)
        
        # Backward pass
        self.model.zero_grad()
        gradient = self.loss_fn.gradient(predictions, y_batch)
        self.model.backward(gradient)
        
        # Mise à jour des paramètres
        self.optimizer.step(self.model.gradients)
        
        return loss
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> float:
        """Évalue le modèle sur un ensemble de données"""
        predictions = self.model.forward(X)
        return self.loss_fn(predictions, y)
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, List[float]]:
        """Entraîne le modèle"""
        # Diviser les données en ensembles d'entraînement et de validation
        n_samples = len(X)
        n_val = int(n_samples * self.validation_split)
        indices = np.random.permutation(n_samples)
        
        train_indices = indices[n_val:]
        val_indices = indices[:n_val]
        
        X_train, y_train = X[train_indices], y[train_indices]
        X_val, y_val = X[val_indices], y[val_indices]
        
        best_val_loss = float("inf")
        patience_counter = 0
        
        for epoch in range(self.n_epochs):
            # Mode entraînement
            self.model.train()
            
            # Mélanger les données d'entraînement
            train_indices = np.random.permutation(len(X_train))
            X_train_shuffled = X_train[train_indices]
            y_train_shuffled = y_train[train_indices]
            
            # Entraînement par lots
            train_losses = []
            for i in range(0, len(X_train), self.batch_size):
                batch_X = X_train_shuffled[i:i + self.batch_size]
                batch_y = y_train_shuffled[i:i + self.batch_size]
                
                # Forward pass
                predictions = self.model.forward(batch_X)
                loss = self.loss_fn(predictions, batch_y)
                
                # Backward pass
                self.model.zero_grad()
                grad = self.loss_fn.gradient(predictions, batch_y)
                self.model.backward(grad)
                
                # Mise à jour des paramètres
                self.optimizer.step(self.model.get_params())
                
                train_losses.append(loss)
            
            # Évaluation sur l'ensemble de validation
            self.model.eval()
            val_predictions = self.model.forward(X_val)
            val_loss = self.loss_fn(val_predictions, y_val)
            
            # Mettre à jour les métriques
            train_metrics = self.metrics.update(
                self.model.forward(X_train),
                y_train
            )
            val_metrics = self.metrics.update(
                val_predictions,
                y_val
            )
            
            # Enregistrer l'historique
            self.history["train_loss"].append(np.mean(train_losses))
            self.history["val_loss"].append(val_loss)
            for metric_name, value in val_metrics.items():
                self.history[metric_name].append(value)
            
            # Sauvegarder dans Redis si configuré
            if self.redis_storage:
                self.redis_storage.save_metrics(
                    self.run_id,
                    self.history,
                    {
                        **self.run_metadata,
                        "current_epoch": epoch + 1,
                        "best_val_loss": best_val_loss,
                        "patience_counter": patience_counter
                    }
                )
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.early_stopping_patience:
                    print(f"Early stopping à l'époque {epoch + 1}")
                    break
            
            # Afficher les métriques
            print(f"Époque {epoch + 1}/{self.n_epochs}")
            print(f"Train Loss: {np.mean(train_losses):.4f}")
            print(f"Val Loss: {val_loss:.4f}")
            print("Métriques de validation:")
            for metric_name, value in val_metrics.items():
                print(f"{metric_name}: {value:.4f}")
            print()
        
        # Mettre à jour les métadonnées finales
        if self.redis_storage:
            self.run_metadata.update({
                "end_time": datetime.now().isoformat(),
                "final_val_loss": val_loss,
                "best_val_loss": best_val_loss,
                "total_epochs": epoch + 1
            })
            self.redis_storage.save_metrics(
                self.run_id,
                self.history,
                self.run_metadata
            )
        
        return self.history 