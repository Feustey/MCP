import numpy as np
from .base import BaseLoss

class MSE(BaseLoss):
    """Erreur quadratique moyenne (Mean Squared Error)"""
    
    def compute(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """
        Calcule l'erreur quadratique moyenne
        
        Args:
            y_pred: Prédictions du modèle
            y_true: Valeurs réelles
            
        Returns:
            Valeur de la MSE
        """
        return np.mean((y_pred - y_true) ** 2)
    
    def gradient(self, y_pred: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """
        Calcule le gradient de la MSE
        
        Args:
            y_pred: Prédictions du modèle
            y_true: Valeurs réelles
            
        Returns:
            Gradient de la MSE
        """
        return 2 * (y_pred - y_true) / len(y_true) 