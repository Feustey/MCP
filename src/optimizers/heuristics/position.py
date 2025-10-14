"""
Network Position Heuristic - Score basé sur la position dans le réseau
Dernière mise à jour: 12 octobre 2025

Évalue la position stratégique:
- Hub central vs edge
- Connectivité régionale
- Position dans le routing
"""

from typing import Dict, Any, Optional

from .base import BaseHeuristic, HeuristicResult
import structlog

logger = structlog.get_logger(__name__)


class PositionHeuristic(BaseHeuristic):
    """
    Heuristique de position réseau
    
    Score élevé si:
    - Position centrale (hub)
    - Bien connecté régionalement
    - Utilisé dans routing paths
    """
    
    async def calculate(
        self,
        channel_data: Dict[str, Any],
        node_data: Optional[Dict[str, Any]] = None,
        network_data: Optional[Dict[str, Any]] = None
    ) -> HeuristicResult:
        """
        Calcule le score de position
        
        Utilise:
        - Eigenvector centrality (si disponible)
        - PageRank (si disponible)
        - Clustering coefficient
        """
        details = {}
        raw_values = {}
        
        # Eigenvector centrality (influence dans le réseau)
        eigenvector = network_data.get("eigenvector_centrality", 0.0) if network_data else 0.0
        raw_values["eigenvector_centrality"] = eigenvector
        
        # Normaliser (typiquement 0.0 - 0.05 pour les hubs)
        eigenvector_score = min(eigenvector * 20, 1.0)
        
        # PageRank (si disponible)
        pagerank = network_data.get("pagerank", 0.0) if network_data else 0.0
        raw_values["pagerank"] = pagerank
        
        # Normaliser
        pagerank_score = min(pagerank * 1000, 1.0)
        
        # Clustering coefficient (connectivité des voisins)
        clustering = network_data.get("clustering_coefficient", 0.5) if network_data else 0.5
        raw_values["clustering"] = clustering
        
        # Un bon hub a un clustering faible (connecte différentes régions)
        # Un edge node a un clustering élevé (groupe local)
        # Pour routing, clustering faible est meilleur
        clustering_score = 1.0 - clustering
        
        # Si données réseau disponibles
        if eigenvector > 0 or pagerank > 0:
            score = (
                eigenvector_score * 0.5 +
                pagerank_score * 0.3 +
                clustering_score * 0.2
            )
            details["position_type"] = "Calculated from network metrics"
        else:
            # Fallback: estimer depuis le nombre de canaux du peer
            peer_channels = node_data.get("num_channels", 0) if node_data else 0
            
            if peer_channels >= 50:
                score = 0.8  # Probablement un hub
                details["position_type"] = "Hub (estimated)"
            elif peer_channels >= 20:
                score = 0.6  # Bien connecté
                details["position_type"] = "Well-connected"
            elif peer_channels >= 10:
                score = 0.4  # Routeur moyen
                details["position_type"] = "Regular router"
            else:
                score = 0.2  # Edge node
                details["position_type"] = "Edge node"
        
        weighted_score = score * self.weight
        
        logger.debug(
            "position_calculated",
            channel_id=channel_data.get("channel_id"),
            score=score
        )
        
        return HeuristicResult(
            name=self.name,
            score=score,
            weight=self.weight,
            weighted_score=weighted_score,
            details=details,
            raw_values=raw_values
        )

