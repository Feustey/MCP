from typing import Dict
import numpy as np
from .base_optimizer import BaseOptimizer

class Adam(BaseOptimizer):
    def __init__(self, 
                 parameters: Dict[str, np.ndarray], 
                 learning_rate: float = 0.001,
                 beta1: float = 0.9, 
                 beta2: float = 0.999, 
                 epsilon: float = 1e-8):
        super().__init__(parameters, learning_rate)
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.m = {k: np.zeros_like(v) for k, v in parameters.items()}
        self.v = {k: np.zeros_like(v) for k, v in parameters.items()}
        self.t = 0
    
    def step(self, gradients: Dict[str, np.ndarray]):
        """Mise à jour des paramètres avec Adam"""
        self.t += 1
        
        for key in self.parameters:
            # Mise à jour des moments
            self.m[key] = self.beta1 * self.m[key] + (1 - self.beta1) * gradients[key]
            self.v[key] = self.beta2 * self.v[key] + (1 - self.beta2) * np.square(gradients[key])
            
            # Correction du biais
            m_hat = self.m[key] / (1 - self.beta1**self.t)
            v_hat = self.v[key] / (1 - self.beta2**self.t)
            
            # Mise à jour des paramètres
            self.parameters[key] -= self.lr * m_hat / (np.sqrt(v_hat) + self.epsilon) 