#!/usr/bin/env python3
"""
Métriques de calibration explicites pour le simulateur stochastique.
Ce module définit les métriques utilisées pour calibrer le simulateur avec des données de nœuds réels.

Dernière mise à jour: 8 mai 2025
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("calibration_metrics")

@dataclass
class MetricConfig:
    """Configuration pour une métrique de calibration spécifique"""
    description: str
    bins: np.ndarray = None
    test: str = "kolmogorov_smirnov"
    threshold: float = 0.05
    weight: float = 1.0


class CalibrationMetrics:
    """
    Système de métriques de calibration pour le simulateur stochastique.
    Définit les distributions et tests statistiques utilisés pour comparer
    les données simulées avec les données réelles.
    """
    
    def __init__(self):
        """Initialise le système de métriques de calibration"""
        self.metrics = {
            "forward_volume_distribution": MetricConfig(
                description="Distribution du volume forwardé par canal par jour",
                bins=np.logspace(3, 7, 20),  # 1k sats à 10M sats (échelle log)
                test="kolmogorov_smirnov",
                threshold=0.05,
                weight=0.4
            ),
            "success_rate_distribution": MetricConfig(
                description="Distribution des taux de réussite par canal",
                bins=np.linspace(0, 1, 20),  # 0% à 100% (échelle linéaire)
                test="kolmogorov_smirnov",
                threshold=0.05,
                weight=0.3
            ),
            "liquidity_ratio_evolution": MetricConfig(
                description="Distribution des variations local_balance/capacity entre t et t+1",
                bins=np.linspace(-0.3, 0.3, 20),  # -30% à +30% (échelle linéaire)
                test="jensen_shannon_divergence",
                threshold=0.1,
                weight=0.2
            ),
            "fee_elasticity": MetricConfig(
                description="Variation du volume suite à une variation des frais",
                test="pearson_correlation",
                threshold=0.6,
                weight=0.1
            )
        }
        
        self.calibration_results = []
    
    def get_metric_config(self, metric_name: str) -> Optional[MetricConfig]:
        """
        Récupère la configuration d'une métrique spécifique
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            Configuration de la métrique ou None si non trouvée
        """
        return self.metrics.get(metric_name)
    
    def get_all_metrics(self) -> Dict[str, MetricConfig]:
        """
        Récupère toutes les configurations de métriques
        
        Returns:
            Dictionnaire des configurations de métriques
        """
        return self.metrics.copy()
    
    def add_calibration_result(self, result: Dict[str, Any]) -> None:
        """
        Ajoute un résultat de calibration à l'historique
        
        Args:
            result: Résultat de calibration
        """
        self.calibration_results.append(result)
    
    def get_metric_weights(self) -> Dict[str, float]:
        """
        Récupère les poids de chaque métrique pour le calcul de la divergence totale
        
        Returns:
            Dictionnaire des poids par métrique
        """
        return {name: config.weight for name, config in self.metrics.items()}
    
    def get_convergence_threshold(self) -> float:
        """
        Calcule le seuil de convergence global à partir des seuils individuels
        
        Returns:
            Seuil de convergence global
        """
        # Moyenne pondérée des seuils individuels
        total_weight = sum(config.weight for config in self.metrics.values())
        if total_weight == 0:
            return 0.1  # Valeur par défaut
            
        weighted_sum = sum(config.threshold * config.weight 
                          for config in self.metrics.values())
        
        return weighted_sum / total_weight 