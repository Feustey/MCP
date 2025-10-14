"""
Base Heuristic - Classe de base pour toutes les heuristiques
Dernière mise à jour: 12 octobre 2025
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HeuristicResult:
    """Résultat d'une heuristique"""
    name: str
    score: float  # 0.0 - 1.0
    weight: float  # Poids de l'heuristique
    weighted_score: float  # score * weight
    details: Dict[str, Any]
    raw_values: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "weighted_score": self.weighted_score,
            "details": self.details,
            "raw_values": self.raw_values
        }


class BaseHeuristic(ABC):
    """
    Classe de base pour toutes les heuristiques
    
    Chaque heuristique doit:
    - Calculer un score entre 0.0 et 1.0
    - Fournir des détails sur le calcul
    - Être configurable via poids
    """
    
    def __init__(self, weight: float = 1.0, enabled: bool = True):
        """
        Initialise l'heuristique
        
        Args:
            weight: Poids de l'heuristique (0.0 - 1.0)
            enabled: Si l'heuristique est activée
        """
        self.weight = weight
        self.enabled = enabled
        self.name = self.__class__.__name__.replace("Heuristic", "")
    
    @abstractmethod
    async def calculate(
        self,
        channel_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> HeuristicResult:
        """
        Calcule le score de l'heuristique
        
        Args:
            channel_data: Données du canal
            node_data: Données du nœud (optionnel)
            network_data: Données du réseau (optionnel)
            
        Returns:
            Résultat de l'heuristique
        """
        pass
    
    def normalize_score(self, value: float, min_val: float, max_val: float) -> float:
        """
        Normalise un score entre 0.0 et 1.0
        
        Args:
            value: Valeur à normaliser
            min_val: Valeur minimum
            max_val: Valeur maximum
            
        Returns:
            Score normalisé (0.0 - 1.0)
        """
        if max_val == min_val:
            return 0.5  # Valeur par défaut si pas de variance
        
        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))  # Clamp entre 0 et 1
    
    def sigmoid(self, x: float, center: float = 0.0, steepness: float = 1.0) -> float:
        """
        Fonction sigmoïde pour normalisation douce
        
        Args:
            x: Valeur d'entrée
            center: Centre de la courbe
            steepness: Raideur de la courbe
            
        Returns:
            Valeur entre 0.0 et 1.0
        """
        import math
        return 1.0 / (1.0 + math.exp(-steepness * (x - center)))

