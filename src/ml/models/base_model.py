from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any

class BaseModel(ABC):
    def __init__(self):
        self.parameters: Dict[str, np.ndarray] = {}
        self.gradients: Dict[str, np.ndarray] = {}
    
    @abstractmethod
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant"""
        pass
    
    @abstractmethod
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation"""
        pass
    
    def zero_grad(self):
        """Réinitialise les gradients"""
        self.gradients = {k: np.zeros_like(v) for k, v in self.parameters.items()}
    
    def get_parameters(self) -> Dict[str, np.ndarray]:
        """Retourne les paramètres du modèle"""
        return self.parameters
    
    def set_parameters(self, parameters: Dict[str, np.ndarray]):
        """Met à jour les paramètres du modèle"""
        self.parameters = parameters 