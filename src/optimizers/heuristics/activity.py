"""
Activity Heuristic - Heuristique d'activité de routage

Évalue l'activité de routage d'un canal basée sur:
- Volume de forwards
- Fréquence des forwards
- Taux de succès
- Fees gagnés

Auteur: MCP Team
Date: 13 octobre 2025
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class ActivityHeuristic:
    """
    Calcule le score d'activité de routage.
    
    Score élevé = canal très actif et rentable
    """
    
    def __init__(self, weight: float = 0.20):
        """
        Initialise l'heuristique.
        
        Args:
            weight: Poids de cette heuristique (défaut: 20%)
        """
        self.weight = weight
        self.name = "Activity"
        
        # Seuils (valeurs typiques pour un bon canal)
        self.good_forwards_per_day = 10
        self.good_volume_per_day = 1_000_000  # 1M sats
        self.good_fees_per_day = 100  # 100 sats
        
        logger.info("activity_heuristic_initialized", weight=weight)
    
    def calculate(self, 
                 channel_data: Dict[str, Any],
                 timeframe_days: int = 30) -> float:
        """
        Calcule le score d'activité.
        
        Args:
            channel_data: Données du canal
            timeframe_days: Période d'analyse (défaut: 30 jours)
            
        Returns:
            Score 0.0 - 1.0
        """
        # Métriques d'activité
        total_forwards = channel_data.get("total_forwards", 0)
        total_volume = channel_data.get("total_volume_sats", 0)
        total_fees = channel_data.get("total_fees_earned_sats", 0)
        success_rate = channel_data.get("forward_success_rate", 0.0)
        
        # Normaliser par jour
        forwards_per_day = total_forwards / timeframe_days
        volume_per_day = total_volume / timeframe_days
        fees_per_day = total_fees / timeframe_days
        
        # Calculer les scores individuels
        forwards_score = min(1.0, forwards_per_day / self.good_forwards_per_day)
        volume_score = min(1.0, volume_per_day / self.good_volume_per_day)
        fees_score = min(1.0, fees_per_day / self.good_fees_per_day)
        success_score = success_rate  # Déjà 0-1
        
        # Score composite pondéré
        activity_score = (
            forwards_score * 0.25 +
            volume_score * 0.30 +
            fees_score * 0.30 +
            success_score * 0.15
        )
        
        # Pénalité si aucune activité récente
        days_since_last = channel_data.get("days_since_last_forward", 0)
        if days_since_last > 7:
            penalty = min(0.5, days_since_last / 30)  # Max 50% pénalité
            activity_score *= (1 - penalty)
        
        logger.debug("activity_calculated",
                    channel_id=channel_data.get("channel_id"),
                    forwards_per_day=forwards_per_day,
                    volume_per_day=volume_per_day,
                    fees_per_day=fees_per_day,
                    success_rate=success_rate,
                    score=activity_score)
        
        return max(0.0, min(1.0, activity_score))
    
    def get_activity_tier(self, score: float) -> str:
        """
        Retourne le tier d'activité.
        
        Args:
            score: Score calculé
            
        Returns:
            Tier: "very_active", "active", "moderate", "low", "inactive"
        """
        if score >= 0.8:
            return "very_active"
        elif score >= 0.6:
            return "active"
        elif score >= 0.4:
            return "moderate"
        elif score >= 0.2:
            return "low"
        else:
            return "inactive"
    
    def get_explanation(self, score: float, channel_data: Dict[str, Any]) -> str:
        """
        Génère une explication du score.
        
        Args:
            score: Score calculé
            channel_data: Données du canal
            
        Returns:
            Explication textuelle
        """
        tier = self.get_activity_tier(score)
        
        forwards = channel_data.get("total_forwards", 0)
        volume = channel_data.get("total_volume_sats", 0)
        fees = channel_data.get("total_fees_earned_sats", 0)
        success_rate = channel_data.get("forward_success_rate", 0.0) * 100
        
        explanations = {
            "very_active": f"Highly active channel - {forwards} forwards, {volume:,} sats volume, {success_rate:.1f}% success rate",
            "active": f"Active channel - {forwards} forwards, {volume:,} sats volume, earning {fees:,} sats",
            "moderate": f"Moderately active - {forwards} forwards, some routing activity",
            "low": f"Low activity - {forwards} forwards, limited routing",
            "inactive": f"Inactive channel - {forwards} forwards, minimal or no routing"
        }
        
        return explanations.get(tier, "Activity status unclear")
    
    def calculate_revenue_per_sat(self, channel_data: Dict[str, Any]) -> float:
        """
        Calcule le revenue par sat de capacité.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Revenue (fees / capacity) en ppm
        """
        capacity = channel_data.get("capacity", 0)
        fees = channel_data.get("total_fees_earned_sats", 0)
        
        if capacity == 0:
            return 0.0
        
        # Revenue en parts per million
        revenue_ppm = (fees / capacity) * 1_000_000
        
        return revenue_ppm
    
    def is_profitable(self, 
                     channel_data: Dict[str, Any],
                     min_revenue_ppm: float = 100.0) -> bool:
        """
        Détermine si le canal est rentable.
        
        Args:
            channel_data: Données du canal
            min_revenue_ppm: Revenue minimum attendu (ppm)
            
        Returns:
            True si rentable
        """
        revenue = self.calculate_revenue_per_sat(channel_data)
        return revenue >= min_revenue_ppm
