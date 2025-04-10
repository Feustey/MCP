import numpy as np
from .base_loss import BaseLoss

class MAE(BaseLoss):
    def __init__(self):
        super().__init__()
    
    def __call__(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule l'erreur absolue moyenne"""
        return np.mean(np.abs(predictions - targets))
    
    def gradient(self, predictions: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Calcule le gradient de l'erreur absolue moyenne"""
        m = predictions.shape[0]
        diff = predictions - targets
        
        # Gradient avec signe
        return np.sign(diff) / m 