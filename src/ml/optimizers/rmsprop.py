from typing import Dict
import numpy as np
from .base_optimizer import BaseOptimizer

class RMSprop(BaseOptimizer):
    def __init__(self, 
                 parameters: Dict[str, np.ndarray], 
                 learning_rate: float = 0.001,
                 alpha: float = 0.99,
                 epsilon: float = 1e-8):
        super().__init__(parameters, learning_rate)
        self.alpha = alpha
        self.epsilon = epsilon
        self.v = {k: np.zeros_like(v) for k, v in parameters.items()}
    
    def step(self, gradients: Dict[str, np.ndarray]):
        """Mise à jour des paramètres avec RMSprop"""
        for key in self.parameters:
            # Mise à jour de la moyenne mobile des carrés des gradients
            self.v[key] = self.alpha * self.v[key] + (1 - self.alpha) * np.square(gradients[key])
            
            # Mise à jour des paramètres
            self.parameters[key] -= self.lr * gradients[key] / (np.sqrt(self.v[key]) + self.epsilon) 