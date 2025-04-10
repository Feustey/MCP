import numpy as np
from typing import Dict, Tuple, Optional, List, Union

class Layer:
    def __init__(self):
        self.input_shape: Optional[Tuple[int, ...]] = None
        self.output_shape: Optional[Tuple[int, ...]] = None
        self.parameters: Dict[str, np.ndarray] = {}
        self.gradients: Dict[str, np.ndarray] = {}
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant"""
        raise NotImplementedError
    
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation"""
        raise NotImplementedError
    
    def zero_grad(self):
        """Réinitialise les gradients"""
        self.gradients = {k: np.zeros_like(v) for k, v in self.parameters.items()}

class Dense(Layer):
    def __init__(self, units: int, activation: str = 'sigmoid', input_dim: Optional[int] = None):
        super().__init__()
        self.units = units
        self.activation = activation
        self.input_dim = input_dim
        
        if input_dim is not None:
            self.build(input_dim)
    
    def build(self, input_dim: int):
        """Initialise les poids et biais"""
        self.input_dim = input_dim
        self.parameters['W'] = np.random.randn(input_dim, self.units) * 0.01
        self.parameters['b'] = np.zeros((1, self.units))
        self.input_shape = (input_dim,)
        self.output_shape = (self.units,)
    
    def _activation(self, x: np.ndarray) -> np.ndarray:
        """Applique la fonction d'activation"""
        if self.activation == 'sigmoid':
            return 1 / (1 + np.exp(-x))
        elif self.activation == 'relu':
            return np.maximum(0, x)
        elif self.activation == 'tanh':
            return np.tanh(x)
        else:
            raise ValueError(f"Activation '{self.activation}' non supportée")
    
    def _activation_derivative(self, x: np.ndarray) -> np.ndarray:
        """Calcule la dérivée de la fonction d'activation"""
        if self.activation == 'sigmoid':
            return x * (1 - x)
        elif self.activation == 'relu':
            return np.where(x > 0, 1, 0)
        elif self.activation == 'tanh':
            return 1 - np.square(x)
        else:
            raise ValueError(f"Activation '{self.activation}' non supportée")
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant"""
        self.input = X
        self.z = np.dot(X, self.parameters['W']) + self.parameters['b']
        self.output = self._activation(self.z)
        return self.output
    
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation"""
        m = gradient.shape[0]
        
        # Gradient de l'activation
        dZ = gradient * self._activation_derivative(self.output)
        
        # Gradient des poids et biais
        self.gradients['W'] = np.dot(self.input.T, dZ) / m
        self.gradients['b'] = np.sum(dZ, axis=0, keepdims=True) / m
        
        # Gradient pour la couche précédente
        return np.dot(dZ, self.parameters['W'].T)

class Dropout(Layer):
    def __init__(self, rate: float = 0.5, training: bool = True):
        super().__init__()
        self.rate = rate
        self.training = training
        self.mask = None
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant avec dropout"""
        if self.training:
            self.mask = np.random.binomial(1, 1 - self.rate, size=X.shape) / (1 - self.rate)
            return X * self.mask
        return X
    
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation avec dropout"""
        if self.training:
            return gradient * self.mask
        return gradient

class BatchNormalization(Layer):
    def __init__(self, epsilon: float = 1e-7, momentum: float = 0.9):
        super().__init__()
        self.epsilon = epsilon
        self.momentum = momentum
        self.running_mean = None
        self.running_var = None
        self.training = True
    
    def build(self, input_shape: Tuple[int, ...]):
        """Initialise les paramètres de normalisation"""
        self.input_shape = input_shape
        self.output_shape = input_shape
        
        # Paramètres appris
        self.parameters['gamma'] = np.ones(input_shape)
        self.parameters['beta'] = np.zeros(input_shape)
        
        # Statistiques d'exécution
        self.running_mean = np.zeros(input_shape)
        self.running_var = np.ones(input_shape)
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        """Propagation avant avec normalisation par lots"""
        if self.training:
            # Calcul des statistiques sur le lot
            batch_mean = np.mean(X, axis=0)
            batch_var = np.var(X, axis=0)
            
            # Mise à jour des statistiques d'exécution
            self.running_mean = (self.momentum * self.running_mean + 
                                (1 - self.momentum) * batch_mean)
            self.running_var = (self.momentum * self.running_var + 
                               (1 - self.momentum) * batch_var)
            
            # Normalisation
            self.X_norm = (X - batch_mean) / np.sqrt(batch_var + self.epsilon)
        else:
            # Utilisation des statistiques d'exécution
            self.X_norm = (X - self.running_mean) / np.sqrt(self.running_var + self.epsilon)
        
        # Échelle et décalage
        return self.parameters['gamma'] * self.X_norm + self.parameters['beta']
    
    def backward(self, gradient: np.ndarray) -> np.ndarray:
        """Rétropropagation avec normalisation par lots"""
        m = gradient.shape[0]
        
        # Gradient de l'échelle et du décalage
        self.gradients['gamma'] = np.sum(gradient * self.X_norm, axis=0)
        self.gradients['beta'] = np.sum(gradient, axis=0)
        
        # Gradient de la normalisation
        dX_norm = gradient * self.parameters['gamma']
        
        # Gradient de la variance
        dVar = np.sum(dX_norm * (self.X_norm - self.running_mean) * -0.5 * 
                      np.power(self.running_var + self.epsilon, -1.5), axis=0)
        
        # Gradient de la moyenne
        dMean = np.sum(dX_norm * -1/np.sqrt(self.running_var + self.epsilon), axis=0) + \
                dVar * np.mean(-2 * (self.X_norm - self.running_mean), axis=0)
        
        # Gradient pour la couche précédente
        return (dX_norm / np.sqrt(self.running_var + self.epsilon) + 
                dVar * 2 * (self.X_norm - self.running_mean) / m + 
                dMean / m) 