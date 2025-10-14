"""
Liquidity Heuristic - Heuristique d'équilibre de liquidité

Évalue l'équilibre de la liquidité dans un canal pour déterminer
son potentiel de routage bidirectionnel.

Métriques:
- Ratio local/remote balance
- Distribution de la liquidité
- Historique des variations
- Capacité de routage

Auteur: MCP Team
Date: 13 octobre 2025
"""

from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class LiquidityHeuristic:
    """
    Calcule le score d'équilibre de liquidité.
    
    Score optimal = liquidité équilibrée (proche de 50/50)
    """
    
    def __init__(self, weight: float = 0.25):
        """
        Initialise l'heuristique.
        
        Args:
            weight: Poids de cette heuristique (défaut: 25%)
        """
        self.weight = weight
        self.name = "Liquidity"
        
        # Zone optimale: 40-60%
        self.optimal_min = 0.40
        self.optimal_max = 0.60
        
        logger.info("liquidity_heuristic_initialized", weight=weight)
    
    def calculate(self, channel_data: Dict[str, Any]) -> float:
        """
        Calcule le score de liquidité.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        local_balance = channel_data.get("local_balance", 0)
        remote_balance = channel_data.get("remote_balance", 0)
        capacity = local_balance + remote_balance
        
        if capacity == 0:
            logger.warning("zero_capacity", channel_id=channel_data.get("channel_id"))
            return 0.0
        
        # Ratio local
        local_ratio = local_balance / capacity
        
        # Score basé sur la distance à l'équilibre optimal (50%)
        score = self._calculate_balance_score(local_ratio)
        
        # Bonus si proche de la zone optimale
        if self.optimal_min <= local_ratio <= self.optimal_max:
            score += 0.1  # Bonus 10%
            score = min(1.0, score)
        
        # Pénalité si très déséquilibré
        if local_ratio < 0.1 or local_ratio > 0.9:
            score *= 0.5  # Pénalité 50%
        
        logger.debug("liquidity_calculated",
                    channel_id=channel_data.get("channel_id"),
                    local_ratio=local_ratio,
                    score=score)
        
        return score
    
    def _calculate_balance_score(self, ratio: float) -> float:
        """
        Calcule le score basé sur le ratio.
        
        Formule: 1.0 - (2 * |ratio - 0.5|)
        
        Args:
            ratio: Ratio local/total (0.0 - 1.0)
            
        Returns:
            Score 0.0 - 1.0
        """
        # Distance à l'équilibre parfait (0.5)
        distance_from_optimal = abs(ratio - 0.5)
        
        # Convertir en score (0 = parfait, 0.5 = pire)
        # Score = 1 - (distance * 2)
        score = 1.0 - (distance_from_optimal * 2.0)
        
        return max(0.0, min(1.0, score))
    
    def get_balance_status(self, channel_data: Dict[str, Any]) -> str:
        """
        Retourne le statut de la balance.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Statut: "balanced", "high_local", "high_remote", "critical"
        """
        local_balance = channel_data.get("local_balance", 0)
        remote_balance = channel_data.get("remote_balance", 0)
        capacity = local_balance + remote_balance
        
        if capacity == 0:
            return "unknown"
        
        local_ratio = local_balance / capacity
        
        if local_ratio >= 0.9:
            return "critical_high_local"
        elif local_ratio >= 0.7:
            return "high_local"
        elif local_ratio >= 0.4:
            return "balanced"
        elif local_ratio >= 0.1:
            return "high_remote"
        else:
            return "critical_high_remote"
    
    def get_explanation(self, score: float, channel_data: Dict[str, Any]) -> str:
        """
        Génère une explication du score.
        
        Args:
            score: Score calculé
            channel_data: Données du canal
            
        Returns:
            Explication textuelle
        """
        status = self.get_balance_status(channel_data)
        local_balance = channel_data.get("local_balance", 0)
        remote_balance = channel_data.get("remote_balance", 0)
        capacity = local_balance + remote_balance
        
        if capacity > 0:
            local_ratio = local_balance / capacity
            local_pct = local_ratio * 100
            remote_pct = (1 - local_ratio) * 100
        else:
            local_pct = remote_pct = 0
        
        explanations = {
            "balanced": f"Well-balanced liquidity ({local_pct:.0f}% local, {remote_pct:.0f}% remote) - optimal for routing",
            "high_local": f"High local balance ({local_pct:.0f}%) - good for outbound, limited inbound",
            "high_remote": f"High remote balance ({remote_pct:.0f}%) - good for inbound, limited outbound",
            "critical_high_local": f"Critical: {local_pct:.0f}% local - rebalancing strongly recommended",
            "critical_high_remote": f"Critical: {remote_pct:.0f}% remote - rebalancing strongly recommended",
            "unknown": "Unable to assess balance"
        }
        
        return explanations.get(status, "Balance status unclear")
    
    def suggest_rebalance_amount(self, channel_data: Dict[str, Any]) -> int:
        """
        Suggère un montant de rebalancing.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Montant suggéré en sats (positif = envoyer, négatif = recevoir)
        """
        local_balance = channel_data.get("local_balance", 0)
        remote_balance = channel_data.get("remote_balance", 0)
        capacity = local_balance + remote_balance
        
        if capacity == 0:
            return 0
        
        # Target: 50% local
        target_local = capacity // 2
        difference = local_balance - target_local
        
        # Arrondir aux 10000 sats les plus proches
        suggested = (difference // 10000) * 10000
        
        logger.info("rebalance_suggested",
                   channel_id=channel_data.get("channel_id"),
                   suggested_amount=suggested)
        
        return suggested
