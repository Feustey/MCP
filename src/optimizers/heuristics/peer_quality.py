"""
Heuristique #7: Peer Quality Score

Évalue la qualité du nœud pair :
- Réputation du pair
- Nombre de canaux du pair
- Capacité totale du pair
- Centralité du pair dans le réseau

Score: 0-100 (100 = pair de très haute qualité)
"""

import logging
from typing import Dict, Any
import math

logger = logging.getLogger(__name__)


def calculate_peer_quality_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    **kwargs
) -> float:
    """Calcule le score de qualité du pair."""
    score = 0.0
    weights = {
        "reputation": 0.30,
        "connectivity": 0.30,
        "capacity": 0.25,
        "activity": 0.15
    }
    
    try:
        peer_data = channel.get("peer_node_data", {})
        
        score += _calculate_reputation_score(peer_data) * weights["reputation"]
        score += _calculate_connectivity_score(peer_data) * weights["connectivity"]
        score += _calculate_capacity_score(peer_data) * weights["capacity"]
        score += _calculate_activity_score(peer_data) * weights["activity"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Peer Quality = {score:.2f}")
    except Exception as e:
        logger.error(f"Erreur calcul peer quality: {e}")
        score = 65.0
    
    return min(100.0, max(0.0, score))


def _calculate_reputation_score(peer_data: Dict[str, Any]) -> float:
    """Score de réputation du pair."""
    # Basé sur rankings externes (Amboss, 1ML, etc.)
    amboss_rank = peer_data.get("amboss_rank")
    oneml_rank = peer_data.get("oneml_rank")
    
    if amboss_rank:
        # Top 100 = 100 points, top 1000 = 80 points, etc.
        if amboss_rank <= 100:
            return 100.0
        elif amboss_rank <= 500:
            return 90 - ((amboss_rank - 100) / 400) * 10
        elif amboss_rank <= 1000:
            return 80 - ((amboss_rank - 500) / 500) * 10
        elif amboss_rank <= 5000:
            return 70 - ((amboss_rank - 1000) / 4000) * 20
        else:
            return max(50, 50 - ((amboss_rank - 5000) / 10000) * 20)
    
    # Fallback: utiliser alias connu
    alias = peer_data.get("alias", "").lower()
    known_good_nodes = ["acinq", "lnbig", "kraken", "bitfinex", "bfx", "blockstream"]
    
    if any(known in alias for known in known_good_nodes):
        return 95.0
    
    return 70.0  # Neutre par défaut


def _calculate_connectivity_score(peer_data: Dict[str, Any]) -> float:
    """Score de connectivité (nombre de canaux)."""
    num_channels = peer_data.get("num_channels", 0)
    
    if num_channels == 0:
        return 20.0
    
    # Échelle logarithmique
    # 10 canaux = 50, 100 canaux = 80, 500+ canaux = 100
    score = (math.log10(num_channels + 1) / math.log10(501)) * 100
    
    return min(100.0, score)


def _calculate_capacity_score(peer_data: Dict[str, Any]) -> float:
    """Score de capacité totale du pair."""
    total_capacity = peer_data.get("total_capacity", 0)
    
    if total_capacity == 0:
        return 20.0
    
    # Échelle logarithmique
    # 10M sats = 40, 100M = 70, 1B+ = 100
    score = (math.log10(total_capacity + 1) - math.log10(10_000_000)) / \
            (math.log10(1_000_000_000) - math.log10(10_000_000)) * 100
    
    return min(100.0, max(20.0, score))


def _calculate_activity_score(peer_data: Dict[str, Any]) -> float:
    """Score d'activité du pair."""
    # Basé sur l'activité de forwarding observée
    forward_count = peer_data.get("total_forwards", 0)
    
    if forward_count == 0:
        return 40.0  # Peut être nouveau
    
    # Plus de forwards = plus actif
    if forward_count < 100:
        return 40 + (forward_count / 100) * 30
    elif forward_count < 1000:
        return 70 + ((forward_count - 100) / 900) * 20
    else:
        return min(100, 90 + math.log10(forward_count - 999) * 5)


def get_peer_quality_components(channel: Dict[str, Any]) -> Dict[str, Any]:
    """Composants détaillés."""
    peer_data = channel.get("peer_node_data", {})
    
    return {
        "reputation": _calculate_reputation_score(peer_data),
        "connectivity": _calculate_connectivity_score(peer_data),
        "capacity": _calculate_capacity_score(peer_data),
        "activity": _calculate_activity_score(peer_data),
        "peer_alias": peer_data.get("alias", "Unknown"),
        "peer_channels": peer_data.get("num_channels", 0),
        "peer_capacity": peer_data.get("total_capacity", 0),
    }
