#!/usr/bin/env python3
"""
Système de métriques objectif pour le simulateur stochastique de nœuds Lightning.
Ce module fournit des outils pour évaluer l'impact des décisions sur les performances du nœud.

Dernière mise à jour: 7 mai 2025
"""

import math
import logging
from typing import Dict, Any, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("performance_metrics")

class PerformanceMetrics:
    """
    Système de métriques pour évaluer les performances d'un nœud Lightning
    et mesurer l'impact des décisions prises par le moteur.
    """
    
    def __init__(self):
        """Initialise le système de métriques avec des valeurs par défaut"""
        self.metrics = {
            "revenue": 0,              # Revenus cumulés en sats
            "opportunity_cost": 0,     # Revenus manqués (forwards ratés)
            "capital_efficiency": 0,   # % du capital utilisé pour forwarding
            "rebalancing_cost": 0,     # Coût des rebalancements
            "peer_retention_rate": 0,  # Conservation des pairs actifs
            "centrality_score": 0,     # Position dans le réseau
            "htlc_success_rate": 0,    # Taux de succès des HTLC
            "channel_stability": 0,    # Stabilité des canaux
            "fee_competitiveness": 0,  # Compétitivité des frais
            "uptime": 0                # Disponibilité du nœud
        }
        self.history = []              # Historique des métriques
    
    def update_metrics(self, new_metrics: Dict[str, float]) -> None:
        """
        Met à jour les métriques avec de nouvelles valeurs
        
        Args:
            new_metrics: Dictionnaire des nouvelles valeurs de métriques
        """
        for key, value in new_metrics.items():
            if key in self.metrics:
                self.metrics[key] = value
            else:
                logger.warning(f"Métrique inconnue: {key}")
        
        # Ajouter à l'historique
        self.history.append(self.metrics.copy())
    
    def calculate_decision_impact(self, before_state: Dict[str, Any], 
                                 after_state: Dict[str, Any], 
                                 timeframe: int) -> Dict[str, float]:
        """
        Calcule l'impact d'une décision sur les métriques
        
        Args:
            before_state: État des métriques avant la décision
            after_state: État des métriques après la décision
            timeframe: Intervalle de temps écoulé (en jours)
            
        Returns:
            Dict contenant les delta normalisés et un score global
        """
        if not before_state or not after_state:
            logger.error("États avant/après manquants pour le calcul d'impact")
            return {"effectiveness_score": 0.0}
        
        impact = {}
        
        # Calculer le delta normalisé pour chaque métrique
        for key in self.metrics.keys():
            before_value = before_state.get(key, 0)
            after_value = after_state.get(key, 0)
            
            # Éviter la division par zéro
            if before_value == 0:
                if after_value == 0:
                    impact[f"{key}_delta"] = 0
                else:
                    impact[f"{key}_delta"] = 1  # Amélioration depuis zéro
            else:
                # Delta en pourcentage
                impact[f"{key}_delta"] = (after_value - before_value) / before_value
        
        # Calculer le ROI spécifique pour le rebalancing
        revenue_delta = after_state.get("revenue", 0) - before_state.get("revenue", 0)
        rebalancing_cost = before_state.get("rebalancing_cost", 0)
        
        if rebalancing_cost > 0:
            impact["roi"] = revenue_delta / rebalancing_cost
        else:
            impact["roi"] = revenue_delta  # Si pas de coût, le ROI est égal au delta de revenus
        
        # Calculer un score d'efficacité global
        impact["effectiveness_score"] = self._calculate_effectiveness(impact)
        
        # Normaliser le score sur une échelle de 0 à 10
        impact["effectiveness_score"] = min(10, max(0, impact["effectiveness_score"] * 10))
        
        return impact
    
    def _calculate_effectiveness(self, impact: Dict[str, float]) -> float:
        """
        Calcule un score d'efficacité composite basé sur plusieurs métriques
        
        Args:
            impact: Dictionnaire des impacts sur différentes métriques
            
        Returns:
            Score composite entre 0 et 1
        """
        # Pondération des différentes métriques
        weights = {
            "revenue_delta": 0.25,
            "opportunity_cost_delta": 0.10,
            "capital_efficiency_delta": 0.20,
            "rebalancing_cost_delta": 0.05,
            "peer_retention_rate_delta": 0.10,
            "htlc_success_rate_delta": 0.15,
            "fee_competitiveness_delta": 0.10,
            "uptime_delta": 0.05
        }
        
        # Score pondéré
        total_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in impact:
                # Limiter les valeurs extrêmes
                value = max(-1, min(1, impact[metric]))
                
                # Normaliser les impacts négatifs
                # Plus une métrique négative est proche de 0, mieux c'est
                if metric in ["opportunity_cost_delta", "rebalancing_cost_delta"]:
                    value = 1 - abs(value) if value <= 0 else 0
                
                total_score += value * weight
                total_weight += weight
        
        # Éviter la division par zéro
        if total_weight == 0:
            return 0
            
        # Normaliser le score
        normalized_score = total_score / total_weight
        
        # Appliquer une fonction sigmoïde pour accentuer les différences autour de 0
        return 1 / (1 + math.exp(-5 * normalized_score))
    
    def get_metrics_snapshot(self) -> Dict[str, float]:
        """
        Retourne une copie des métriques actuelles
        
        Returns:
            Dict contenant les métriques actuelles
        """
        return self.metrics.copy()
    
    def get_historical_trend(self, metric_name: str) -> List[float]:
        """
        Récupère l'historique d'une métrique spécifique
        
        Args:
            metric_name: Nom de la métrique
            
        Returns:
            Liste des valeurs historiques de la métrique
        """
        if not self.history:
            return []
            
        return [snapshot.get(metric_name, 0) for snapshot in self.history]
    
    def reset(self) -> None:
        """Réinitialise toutes les métriques"""
        for key in self.metrics:
            self.metrics[key] = 0
        self.history = [] 