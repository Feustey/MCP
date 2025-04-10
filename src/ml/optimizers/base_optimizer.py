from abc import ABC, abstractmethod
from typing import Dict
import numpy as np

class BaseOptimizer(ABC):
    def __init__(self, parameters: Dict[str, np.ndarray], learning_rate: float = 0.001):
        self.parameters = parameters
        self.lr = learning_rate
    
    @abstractmethod
    def step(self, gradients: Dict[str, np.ndarray]):
        """Mise à jour des paramètres"""
        pass
    
    def get_learning_rate(self) -> float:
        """Retourne le taux d'apprentissage"""
        return self.lr
    
    def set_learning_rate(self, learning_rate: float):
        """Met à jour le taux d'apprentissage"""
        self.lr = learning_rate 