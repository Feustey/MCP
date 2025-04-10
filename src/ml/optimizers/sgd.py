from typing import Dict
import numpy as np
from .base_optimizer import BaseOptimizer

class SGD(BaseOptimizer):
    def __init__(self, 
                 parameters: Dict[str, np.ndarray], 
                 learning_rate: float = 0.01,
                 momentum: float = 0.0,
                 nesterov: bool = False):
        super().__init__(parameters, learning_rate)
        self.momentum = momentum
        self.nesterov = nesterov
        self.velocity = {k: np.zeros_like(v) for k, v in parameters.items()}
    
    def step(self, gradients: Dict[str, np.ndarray]):
        """Mise à jour des paramètres avec SGD"""
        for key in self.parameters:
            if self.momentum > 0:
                # Mise à jour avec momentum
                self.velocity[key] = self.momentum * self.velocity[key] - self.lr * gradients[key]
                
                if self.nesterov:
                    # Nesterov momentum
                    self.parameters[key] += self.momentum * self.velocity[key] - self.lr * gradients[key]
                else:
                    # Momentum classique
                    self.parameters[key] += self.velocity[key]
            else:
                # SGD standard
                self.parameters[key] -= self.lr * gradients[key] 