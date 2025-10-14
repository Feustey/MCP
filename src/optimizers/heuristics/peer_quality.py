"""
Peer Quality Heuristic - Score basé sur la qualité du peer
Dernière mise à jour: 12 octobre 2025

Évalue le peer:
- Réputation
- Nombre de canaux
- Capacité totale
- Rankings externes
"""

from typing import Dict, Any, Optional

from .base import BaseHeuristic, HeuristicResult
import structlog

logger = structlog.get_logger(__name__)


class PeerQualityHeuristic(BaseHeuristic):
    """
    Heuristique de qualité du peer
    
    Score élevé si:
    - Peer bien connecté (>20 canaux)
    - Grande capacité totale
    - Bonne réputation (Amboss, 1ML)
    - Nœud établi
    """
    
    async def calculate(
        self,
        channel_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> HeuristicResult:
        """
        Calcule le score de qualité du peer
        
        Composants:
        - 40% nombre de canaux (hub vs edge)
        - 30% capacité totale
        - 20% réputation externe
        - 10% âge du nœud
        """
        details = {}
        raw_values = {}
        
        if not node_data:
            # Pas de données peer, score neutre
            score = 0.5
            details["error"] = "No peer data available"
        else:
            # Nombre de canaux du peer
            peer_channels = node_data.get("num_channels", 0)
            raw_values["peer_channels"] = peer_channels
            
            # Score canaux (optimal 20-100+)
            if peer_channels >= 100:
                channels_score = 1.0
                details["peer_type"] = "Major hub"
            elif peer_channels >= 50:
                channels_score = 0.9
                details["peer_type"] = "Hub"
            elif peer_channels >= 20:
                channels_score = 0.7
                details["peer_type"] = "Well-connected"
            elif peer_channels >= 10:
                channels_score = 0.5
                details["peer_type"] = "Regular"
            else:
                channels_score = peer_channels / 10 * 0.5
                details["peer_type"] = "Small"
            
            details["peer_channels"] = peer_channels
            
            # Capacité totale du peer
            peer_capacity = node_data.get("total_capacity", 0)
            raw_values["peer_capacity_sats"] = peer_capacity
            
            # Score capacité (>10M sats = très bon)
            capacity_btc = peer_capacity / 100_000_000  # En BTC
            capacity_score = self.sigmoid(capacity_btc, center=0.1, steepness=10)
            details["peer_capacity"] = f"{capacity_btc:.3f} BTC"
            
            # Réputation externe (si disponible)
            reputation = node_data.get("reputation_score", 0.5)
            raw_values["reputation"] = reputation
            reputation_score = reputation  # Déjà normalisé 0-1
            
            if "reputation_source" in node_data:
                details["reputation_source"] = node_data["reputation_source"]
            
            # Âge du nœud
            node_age_days = node_data.get("age_days", 0)
            raw_values["node_age_days"] = node_age_days
            
            # Score âge (>365j = mature)
            if node_age_days >= 365:
                age_score = 1.0
            elif node_age_days >= 180:
                age_score = 0.8
            elif node_age_days >= 90:
                age_score = 0.6
            else:
                age_score = node_age_days / 90 * 0.6
            
            # Score combiné
            score = (
                channels_score * 0.4 +
                capacity_score * 0.3 +
                reputation_score * 0.2 +
                age_score * 0.1
            )
        
        weighted_score = score * self.weight
        
        logger.debug(
            "peer_quality_calculated",
            channel_id=channel_data.get("channel_id"),
            score=score,
            peer_channels=peer_channels if node_data else None
        )
        
        return HeuristicResult(
            name=self.name,
            score=score,
            weight=self.weight,
            weighted_score=weighted_score,
            details=details,
            raw_values=raw_values
        )

