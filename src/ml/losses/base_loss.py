from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple

class BaseLoss(ABC):
    def __init__(self):
        pass
    
    @abstractmethod
    def __call__(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Calcule la perte"""
        pass
    
    @abstractmethod
    def gradient(self, predictions: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Calcule le gradient de la perte"""
        pass
    
    def __str__(self) -> str:
        return self.__class__.__name__ 