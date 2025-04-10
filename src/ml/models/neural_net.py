import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from .base_model import BaseModel
from .layers import Layer, Dense, Dropout, BatchNormalization

class NeuralNetwork(BaseModel):
    def __init__(self, layers: List[Layer]):
        super().__init__()
        self.layers = layers
        self.training = True
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant"""
        current = X
        
        for layer in self.layers:
            if isinstance(layer, (Dropout, BatchNormalization)):
                layer.training = self.training
            current = layer.forward(current)
        
        return current
    
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation"""
        current_gradient = gradient
        
        for layer in reversed(self.layers):
            current_gradient = layer.backward(current_gradient)
            
            # Collecte des gradients
            for key, value in layer.gradients.items():
                self.gradients[f"{layer.__class__.__name__}_{key}"] = value
        
        return current_gradient
    
    def zero_grad(self):
        """Réinitialise les gradients"""
        super().zero_grad()
        for layer in self.layers:
            layer.zero_grad()
    
    def train(self):
        """Passe le modèle en mode entraînement"""
        self.training = True
        for layer in self.layers:
            if isinstance(layer, (Dropout, BatchNormalization)):
                layer.training = True
    
    def eval(self):
        """Passe le modèle en mode évaluation"""
        self.training = False
        for layer in self.layers:
            if isinstance(layer, (Dropout, BatchNormalization)):
                layer.training = False
    
    @classmethod
    def create_mlp(cls, 
                  input_size: int, 
                  hidden_sizes: List[int], 
                  output_size: int,
                  dropout_rate: float = 0.5,
                  use_batch_norm: bool = True) -> 'NeuralNetwork':
        """Crée un réseau de neurones multicouche"""
        layers = []
        
        # Première couche
        layers.append(Dense(hidden_sizes[0], activation='relu', input_dim=input_size))
        if use_batch_norm:
            layers.append(BatchNormalization())
        layers.append(Dropout(rate=dropout_rate))
        
        # Couches cachées
        for units in hidden_sizes[1:]:
            layers.append(Dense(units, activation='relu'))
            if use_batch_norm:
                layers.append(BatchNormalization())
            layers.append(Dropout(rate=dropout_rate))
        
        # Couche de sortie
        layers.append(Dense(output_size, activation='sigmoid'))
        
        return cls(layers) 