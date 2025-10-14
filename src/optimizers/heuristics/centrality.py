"""
Centrality Heuristic - Heuristique de centralité réseau

Évalue la position stratégique d'un nœud dans le réseau Lightning
en fonction de plusieurs métriques de centralité.

Métriques:
- Betweenness centrality: Nombre de chemins passant par ce nœud
- Closeness centrality: Distance moyenne aux autres nœuds
- Eigenvector centrality: Qualité des connexions
- Degree centrality: Nombre de connexions

Auteur: MCP Team
Date: 13 octobre 2025
"""

from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class CentralityHeuristic:
    """
    Calcule le score de centralité d'un canal/nœud.
    
    Score plus élevé = position plus stratégique dans le réseau
    """
    
    def __init__(self, weight: float = 0.20):
        """
        Initialise l'heuristique.
        
        Args:
            weight: Poids de cette heuristique (défaut: 20%)
        """
        self.weight = weight
        self.name = "Centrality"
        
        logger.info("centrality_heuristic_initialized", weight=weight)
    
    def calculate(self, 
                 channel_data: Dict[str, Any],
                 network_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calcule le score de centralité.
        
        Args:
            channel_data: Données du canal
            network_data: Données du graphe réseau (optionnel)
            
        Returns:
            Score 0.0 - 1.0
        """
        peer_pubkey = channel_data.get("peer_pubkey", "")
        
        if not peer_pubkey:
            logger.warning("no_peer_pubkey", channel_id=channel_data.get("channel_id"))
            return 0.5  # Score neutre si pas d'info
        
        # Si on a les données réseau, calculer vraiment
        if network_data:
            return self._calculate_from_network(peer_pubkey, network_data)
        
        # Sinon, approximation basée sur les métriques disponibles
        return self._estimate_centrality(channel_data)
    
    def _calculate_from_network(self, 
                                pubkey: str,
                                network_data: Dict[str, Any]) -> float:
        """
        Calcule la centralité depuis les données réseau.
        
        Args:
            pubkey: Pubkey du peer
            network_data: Graphe du réseau
            
        Returns:
            Score 0.0 - 1.0
        """
        node_metrics = network_data.get("nodes", {}).get(pubkey, {})
        
        # Métriques de centralité normalisées (0-1)
        betweenness = node_metrics.get("betweenness_centrality", 0.0)
        closeness = node_metrics.get("closeness_centrality", 0.0)
        eigenvector = node_metrics.get("eigenvector_centrality", 0.0)
        degree = node_metrics.get("degree_centrality", 0.0)
        
        # Pondération des différentes métriques
        score = (
            betweenness * 0.40 +  # Le plus important pour le routing
            closeness * 0.25 +
            eigenvector * 0.20 +
            degree * 0.15
        )
        
        logger.debug("centrality_calculated",
                    pubkey=pubkey[:16],
                    betweenness=betweenness,
                    closeness=closeness,
                    score=score)
        
        return max(0.0, min(1.0, score))
    
    def _estimate_centrality(self, channel_data: Dict[str, Any]) -> float:
        """
        Estime la centralité depuis les données locales.
        
        Utilise des proxies:
        - Capacité du nœud peer
        - Nombre de canaux du peer
        - Age du nœud peer
        
        Args:
            channel_data: Données du canal
            
        Returns:
            Score estimé 0.0 - 1.0
        """
        peer_capacity = channel_data.get("peer_total_capacity", 0)
        peer_channels = channel_data.get("peer_num_channels", 0)
        peer_age_days = channel_data.get("peer_age_days", 0)
        
        # Normalisation (valeurs typiques du réseau)
        # Top node: ~500M sats capacity, ~500 channels, ~1500 days
        capacity_score = min(1.0, peer_capacity / 500_000_000)
        channels_score = min(1.0, peer_channels / 500)
        age_score = min(1.0, peer_age_days / 1500)
        
        # Score composite
        estimated_score = (
            capacity_score * 0.40 +
            channels_score * 0.40 +
            age_score * 0.20
        )
        
        logger.debug("centrality_estimated",
                    channel_id=channel_data.get("channel_id"),
                    peer_capacity=peer_capacity,
                    peer_channels=peer_channels,
                    score=estimated_score)
        
        return estimated_score
    
    def get_explanation(self, score: float) -> str:
        """
        Génère une explication du score.
        
        Args:
            score: Score calculé
            
        Returns:
            Explication textuelle
        """
        if score >= 0.8:
            return "Highly central node - excellent routing position"
        elif score >= 0.6:
            return "Well-connected node - good routing potential"
        elif score >= 0.4:
            return "Average connectivity - moderate routing value"
        elif score >= 0.2:
            return "Peripheral node - limited routing opportunities"
        else:
            return "Very peripheral - minimal routing value"
