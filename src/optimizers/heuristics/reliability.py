"""
Reliability Heuristic - Heuristique de fiabilité

Évalue la fiabilité et la stabilité d'un canal/nœud.

Métriques:
- Uptime du nœud peer
- Stabilité du canal (pas de force close)
- Age du canal
- Historique des échecs de routage
- Réputation du peer

Auteur: MCP Team
Date: 13 octobre 2025
"""

from typing import Dict, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class ReliabilityHeuristic:
    """
    Calcule le score de fiabilité.
    
    Score élevé = canal/peer stable et fiable
    """
    
    def __init__(self, weight: float = 0.10):
        """
        Initialise l'heuristique.
        
        Args:
            weight: Poids de cette heuristique (défaut: 10%)
        """
        self.weight = weight
        self.name = "Reliability"
        
        # Seuils de fiabilité
        self.good_uptime_pct = 99.0
        self.mature_channel_days = 180  # 6 mois
        self.good_success_rate = 0.95
        
        logger.info("reliability_heuristic_initialized", weight=weight)
    
    def calculate(self, channel_data: Dict[str, Any]) -> float:
        """
        Calcule le score de fiabilité.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        # Composants du score
        uptime_score = self._calculate_uptime_score(channel_data)
        age_score = self._calculate_age_score(channel_data)
        success_score = self._calculate_success_score(channel_data)
        stability_score = self._calculate_stability_score(channel_data)
        
        # Score composite pondéré
        reliability_score = (
            uptime_score * 0.30 +
            age_score * 0.25 +
            success_score * 0.25 +
            stability_score * 0.20
        )
        
        logger.debug("reliability_calculated",
                    channel_id=channel_data.get("channel_id"),
                    uptime=uptime_score,
                    age=age_score,
                    success=success_score,
                    stability=stability_score,
                    score=reliability_score)
        
        return max(0.0, min(1.0, reliability_score))
    
    def _calculate_uptime_score(self, channel_data: Dict[str, Any]) -> float:
        """
        Score basé sur l'uptime du peer.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        uptime_pct = channel_data.get("peer_uptime_percent", 100.0)
        
        if uptime_pct >= self.good_uptime_pct:
            return 1.0
        elif uptime_pct >= 95.0:
            return 0.8
        elif uptime_pct >= 90.0:
            return 0.6
        elif uptime_pct >= 80.0:
            return 0.4
        else:
            return uptime_pct / 100.0
    
    def _calculate_age_score(self, channel_data: Dict[str, Any]) -> float:
        """
        Score basé sur l'âge du canal.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        age_days = channel_data.get("channel_age_days", 0)
        
        # Normaliser par rapport à un canal mature
        age_score = min(1.0, age_days / self.mature_channel_days)
        
        # Bonus pour les très vieux canaux (> 2 ans)
        if age_days > 730:
            age_score = min(1.0, age_score + 0.1)
        
        return age_score
    
    def _calculate_success_score(self, channel_data: Dict[str, Any]) -> float:
        """
        Score basé sur le taux de succès des forwards.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        success_rate = channel_data.get("forward_success_rate", 1.0)
        
        # Pénalité progressive pour taux < 95%
        if success_rate >= self.good_success_rate:
            return 1.0
        else:
            # Score = success_rate / good_success_rate
            return success_rate / self.good_success_rate
    
    def _calculate_stability_score(self, channel_data: Dict[str, Any]) -> float:
        """
        Score basé sur la stabilité (pas de force close, etc).
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score 0.0 - 1.0
        """
        has_force_close_history = channel_data.get("peer_has_force_closes", False)
        force_close_count = channel_data.get("peer_force_close_count", 0)
        
        if has_force_close_history:
            # Pénalité basée sur le nombre
            penalty = min(0.5, force_close_count * 0.1)
            return 1.0 - penalty
        
        # Vérifier si le canal lui-même est stable
        channel_health = channel_data.get("channel_health_score", 1.0)
        
        return channel_health
    
    def get_reliability_tier(self, score: float) -> str:
        """
        Retourne le tier de fiabilité.
        
        Args:
            score: Score calculé
            
        Returns:
            Tier: "excellent", "good", "average", "poor", "unreliable"
        """
        if score >= 0.9:
            return "excellent"
        elif score >= 0.75:
            return "good"
        elif score >= 0.5:
            return "average"
        elif score >= 0.3:
            return "poor"
        else:
            return "unreliable"
    
    def get_explanation(self, score: float, channel_data: Dict[str, Any]) -> str:
        """
        Génère une explication du score.
        
        Args:
            score: Score calculé
            channel_data: Données du canal
            
        Returns:
            Explication textuelle
        """
        tier = self.get_reliability_tier(score)
        
        uptime = channel_data.get("peer_uptime_percent", 100.0)
        age_days = channel_data.get("channel_age_days", 0)
        success_rate = channel_data.get("forward_success_rate", 1.0) * 100
        
        explanations = {
            "excellent": f"Highly reliable - {uptime:.1f}% uptime, {age_days}d old, {success_rate:.1f}% success rate",
            "good": f"Reliable peer - {uptime:.1f}% uptime, {age_days}d old, stable performance",
            "average": f"Average reliability - {uptime:.1f}% uptime, some instability",
            "poor": f"Below-average reliability - {uptime:.1f}% uptime, {success_rate:.1f}% success rate",
            "unreliable": f"Unreliable peer - {uptime:.1f}% uptime, frequent issues"
        }
        
        return explanations.get(tier, "Reliability status unclear")
    
    def identify_reliability_issues(self, channel_data: Dict[str, Any]) -> list:
        """
        Identifie les problèmes de fiabilité spécifiques.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Liste des problèmes identifiés
        """
        issues = []
        
        # Uptime
        uptime = channel_data.get("peer_uptime_percent", 100.0)
        if uptime < 95.0:
            issues.append(f"Low uptime: {uptime:.1f}%")
        
        # Success rate
        success_rate = channel_data.get("forward_success_rate", 1.0)
        if success_rate < 0.90:
            issues.append(f"Low success rate: {success_rate * 100:.1f}%")
        
        # Force closes
        if channel_data.get("peer_has_force_closes", False):
            count = channel_data.get("peer_force_close_count", 0)
            issues.append(f"Peer has {count} force close(s) in history")
        
        # Age très récent
        age_days = channel_data.get("channel_age_days", 0)
        if age_days < 7:
            issues.append(f"Very new channel: {age_days} days old")
        
        # Offline récent
        last_seen = channel_data.get("peer_last_seen", None)
        if last_seen:
            # Si last_seen est un datetime
            if isinstance(last_seen, datetime):
                offline_hours = (datetime.utcnow() - last_seen).total_seconds() / 3600
                if offline_hours > 24:
                    issues.append(f"Peer offline for {offline_hours:.0f} hours")
        
        return issues
    
    def recommend_actions(self, channel_data: Dict[str, Any]) -> list:
        """
        Recommande des actions basées sur les problèmes.
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Liste des actions recommandées
        """
        issues = self.identify_reliability_issues(channel_data)
        actions = []
        
        if not issues:
            actions.append("No action needed - channel is reliable")
            return actions
        
        # Actions spécifiques par type de problème
        for issue in issues:
            if "uptime" in issue.lower():
                actions.append("Monitor peer connectivity - consider closing if uptime doesn't improve")
            
            elif "success rate" in issue.lower():
                actions.append("Investigate routing failures - may need rebalancing or fee adjustment")
            
            elif "force close" in issue.lower():
                actions.append("Exercise caution - peer has history of force closes")
            
            elif "new channel" in issue.lower():
                actions.append("Monitor closely during initial period - reliability not yet established")
            
            elif "offline" in issue.lower():
                actions.append("Check peer status - may be temporarily offline or permanently down")
        
        return actions
