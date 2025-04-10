import numpy as np
from typing import Dict, List, Callable, Union, Any
from abc import ABC, abstractmethod

class Metric(ABC):
    def __init__(self, name: str):
        self.name = name
        self.values: List[float] = []
    
    @abstractmethod
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Met à jour la métrique avec de nouvelles prédictions"""
        pass
    
    def reset(self):
        """Réinitialise la métrique"""
        self.values = []
    
    def get_value(self) -> float:
        """Retourne la valeur actuelle de la métrique"""
        return np.mean(self.values) if self.values else 0.0
    
    def __str__(self) -> str:
        return f"{self.name}: {self.get_value():.4f}"

class Accuracy(Metric):
    def __init__(self, threshold: float = 0.5):
        super().__init__("Accuracy")
        self.threshold = threshold
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule la précision"""
        predictions_binary = (predictions > self.threshold).astype(int)
        accuracy = np.mean(predictions_binary == targets)
        self.values.append(accuracy)
        return accuracy

class Precision(Metric):
    def __init__(self, threshold: float = 0.5):
        super().__init__("Precision")
        self.threshold = threshold
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule la précision"""
        predictions_binary = (predictions > self.threshold).astype(int)
        true_positives = np.sum((predictions_binary == 1) & (targets == 1))
        predicted_positives = np.sum(predictions_binary == 1)
        
        precision = true_positives / predicted_positives if predicted_positives > 0 else 0.0
        self.values.append(precision)
        return precision

class Recall(Metric):
    def __init__(self, threshold: float = 0.5):
        super().__init__("Recall")
        self.threshold = threshold
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule le rappel"""
        predictions_binary = (predictions > self.threshold).astype(int)
        true_positives = np.sum((predictions_binary == 1) & (targets == 1))
        actual_positives = np.sum(targets == 1)
        
        recall = true_positives / actual_positives if actual_positives > 0 else 0.0
        self.values.append(recall)
        return recall

class F1Score(Metric):
    def __init__(self, threshold: float = 0.5):
        super().__init__("F1 Score")
        self.threshold = threshold
        self.precision = Precision(threshold)
        self.recall = Recall(threshold)
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule le score F1"""
        precision = self.precision.update(predictions, targets)
        recall = self.recall.update(predictions, targets)
        
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        self.values.append(f1)
        return f1

class ROCAUC(Metric):
    def __init__(self):
        super().__init__("ROC AUC")
        self.true_positives = []
        self.false_positives = []
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule l'aire sous la courbe ROC"""
        # Trier les prédictions et les cibles
        sorted_indices = np.argsort(predictions.flatten())
        sorted_targets = targets.flatten()[sorted_indices]
        
        # Calculer les taux de vrais positifs et faux positifs
        total_positives = np.sum(targets == 1)
        total_negatives = np.sum(targets == 0)
        
        tpr = np.cumsum(sorted_targets == 1) / total_positives
        fpr = np.cumsum(sorted_targets == 0) / total_negatives
        
        # Calculer l'aire sous la courbe
        auc = np.trapz(tpr, fpr)
        self.values.append(auc)
        return auc

class MetricCollection:
    def __init__(self, metrics: List[Metric]):
        self.metrics = metrics
    
    def update(self, predictions: np.ndarray, targets: np.ndarray) -> Dict[str, float]:
        """Met à jour toutes les métriques"""
        results = {}
        for metric in self.metrics:
            value = metric.update(predictions, targets)
            results[metric.name] = value
        return results
    
    def reset(self):
        """Réinitialise toutes les métriques"""
        for metric in self.metrics:
            metric.reset()
    
    def get_values(self) -> Dict[str, float]:
        """Retourne les valeurs actuelles de toutes les métriques"""
        return {metric.name: metric.get_value() for metric in self.metrics}
    
    def __str__(self) -> str:
        return "\n".join(str(metric) for metric in self.metrics) 