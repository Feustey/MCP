from abc import ABC, abstractmethod
import numpy as np
from typing import Any, Tuple

class BaseLoss(ABC):
    """Classe de base pour les fonctions de perte"""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    def compute(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        """
        Calcule la valeur de la fonction de perte
        
        Args:
            y_pred: Prédictions du modèle
            y_true: Valeurs réelles
            
        Returns:
            Valeur de la perte
        """
        pass
    
    @abstractmethod
    def gradient(self, y_pred: np.ndarray, y_true: np.ndarray) -> np.ndarray:
        """
        Calcule le gradient de la fonction de perte
        
        Args:
            y_pred: Prédictions du modèle
            y_true: Valeurs réelles
            
        Returns:
            Gradient de la perte
        """
        pass
    
    def __call__(self, y_pred: np.ndarray, y_true: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        Calcule à la fois la valeur et le gradient de la perte
        
        Args:
            y_pred: Prédictions du modèle
            y_true: Valeurs réelles
            
        Returns:
            Tuple contenant (valeur de la perte, gradient)
        """
        return self.compute(y_pred, y_true), self.gradient(y_pred, y_true) 