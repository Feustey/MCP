from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseOptimizer(ABC):
    """Classe de base pour les optimiseurs"""
    
    def __init__(self, **kwargs):
        self.config = kwargs
        
    @abstractmethod
    def optimize(self, model: Any, X: Any, y: Any) -> Dict[str, Any]:
        """
        Optimise le modèle avec les données fournies
        
        Args:
            model: Le modèle à optimiser
            X: Les features
            y: Les labels
            
        Returns:
            Dict contenant les résultats de l'optimisation
        """
        pass
    
    @abstractmethod
    def get_best_params(self) -> Dict[str, Any]:
        """
        Retourne les meilleurs paramètres trouvés
        
        Returns:
            Dict contenant les meilleurs paramètres
        """
        pass 