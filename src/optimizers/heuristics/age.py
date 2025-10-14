"""
Age & Stability Heuristic - Score basé sur l'âge et la stabilité du canal
Dernière mise à jour: 12 octobre 2025

Mesure la maturité:
- Âge du canal
- Stabilité sur la durée
- Historique de performance
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseHeuristic, HeuristicResult
import structlog

logger = structlog.get_logger(__name__)


class AgeHeuristic(BaseHeuristic):
    """
    Heuristique d'âge et stabilité
    
    Score élevé si:
    - Canal mature (>90 jours)
    - Pas de problèmes historiques
    - Trend positif
    """
    
    async def calculate(
        self,
        channel_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> HeuristicResult:
        """
        Calcule le score d'âge
        
        Formule:
        - Score augmente avec l'âge (plateau à 180j)
        - Bonus si pas de problèmes
        - Pénalité si canal récent (<7j)
        """
        details = {}
        raw_values = {}
        
        # Calculer l'âge du canal
        opened_at = channel_data.get("opened_at")
        if opened_at:
            if isinstance(opened_at, str):
                opened_at = datetime.fromisoformat(opened_at)
            age_days = (datetime.now() - opened_at).days
        else:
            age_days = channel_data.get("age_days", 0)
        
        raw_values["age_days"] = age_days
        
        # Score basé sur l'âge
        # Progression: 0j=0.0, 7j=0.3, 30j=0.6, 90j=0.9, 180j+=1.0
        if age_days < 7:
            age_score = age_days / 7 * 0.3  # 0.0 - 0.3
            details["maturity"] = "Very young"
        elif age_days < 30:
            age_score = 0.3 + (age_days - 7) / 23 * 0.3  # 0.3 - 0.6
            details["maturity"] = "Young"
        elif age_days < 90:
            age_score = 0.6 + (age_days - 30) / 60 * 0.3  # 0.6 - 0.9
            details["maturity"] = "Mature"
        elif age_days < 180:
            age_score = 0.9 + (age_days - 90) / 90 * 0.1  # 0.9 - 1.0
            details["maturity"] = "Very mature"
        else:
            age_score = 1.0
            details["maturity"] = "Established"
        
        details["age"] = f"{age_days} days"
        
        # Bonus/Pénalités basées sur l'historique
        has_issues = channel_data.get("has_historical_issues", False)
        if has_issues:
            age_score *= 0.8
            details["historical_issues"] = "Yes"
        
        # Score final
        score = age_score
        weighted_score = score * self.weight
        
        logger.debug(
            "age_calculated",
            channel_id=channel_data.get("channel_id"),
            score=score,
            age_days=age_days
        )
        
        return HeuristicResult(
            name=self.name,
            score=score,
            weight=self.weight,
            weighted_score=weighted_score,
            details=details,
            raw_values=raw_values
        )

