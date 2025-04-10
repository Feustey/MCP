import numpy as np
from .base_loss import BaseLoss

class BinaryCrossEntropy(BaseLoss):
    def __init__(self, epsilon: float = 1e-15):
        super().__init__()
        self.epsilon = epsilon
    
    def __call__(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule l'entropie croisée binaire"""
        # Clip pour éviter log(0)
        predictions = np.clip(predictions, self.epsilon, 1 - self.epsilon)
        
        # Calcul de la perte
        return -np.mean(
            targets * np.log(predictions) + 
            (1 - targets) * np.log(1 - predictions)
        )
    
    def gradient(self, predictions: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Calcule le gradient de l'entropie croisée binaire"""
        m = predictions.shape[0]
        predictions = np.clip(predictions, self.epsilon, 1 - self.epsilon)
        
        return (predictions - targets) / m 