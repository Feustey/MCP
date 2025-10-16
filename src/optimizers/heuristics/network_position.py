"""
Heuristique #8: Network Position Score

Évalue la position du canal dans la topologie du réseau :
- Hub vs Edge node
- Importance stratégique
- Potential routing value
- Geographic/logical position

Score: 0-100 (100 = position stratégique optimale)
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_network_position_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Dict[str, Any] = None,
    **kwargs
) -> float:
    """Calcule le score de position réseau."""
    score = 0.0
    weights = {
        "hub_vs_edge": 0.40,
        "strategic": 0.30,
        "routing_value": 0.20,
        "redundancy": 0.10
    }
    
    try:
        score += _calculate_hub_score(channel, node_data, network_graph) * weights["hub_vs_edge"]
        score += _calculate_strategic_score(channel, node_data) * weights["strategic"]
        score += _calculate_routing_value_score(channel) * weights["routing_value"]
        score += _calculate_redundancy_score(channel, node_data) * weights["redundancy"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Network Position = {score:.2f}")
    except Exception as e:
        logger.error(f"Erreur calcul network position: {e}")
        score = 60.0
    
    return min(100.0, max(0.0, score))


def _calculate_hub_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Dict[str, Any] = None
) -> float:
    """Score hub vs edge (plus de canaux = plus hub)."""
    num_channels = len(node_data.get("channels", []))
    
    # Classification:
    # 1-5 canaux = edge (30-50)
    # 6-15 canaux = intermediate (50-70)
    # 16-50 canaux = hub (70-90)
    # 50+ canaux = major hub (90-100)
    
    if num_channels <= 5:
        return 30 + (num_channels / 5) * 20
    elif num_channels <= 15:
        return 50 + ((num_channels - 5) / 10) * 20
    elif num_channels <= 50:
        return 70 + ((num_channels - 15) / 35) * 20
    else:
        return min(100, 90 + ((num_channels - 50) / 50) * 10)


def _calculate_strategic_score(channel: Dict[str, Any], node_data: Dict[str, Any]) -> float:
    """Score d'importance stratégique."""
    # Facteurs:
    # - Connecte à un hub majeur?
    # - Unique path pour certains forwards?
    # - Geographic diversity?
    
    peer_data = channel.get("peer_node_data", {})
    peer_channels = peer_data.get("num_channels", 0)
    
    # Connecter à un gros hub = stratégique
    if peer_channels > 100:
        return 90.0
    elif peer_channels > 50:
        return 80.0
    elif peer_channels > 20:
        return 70.0
    else:
        return 60.0


def _calculate_routing_value_score(channel: Dict[str, Any]) -> float:
    """Score de valeur de routing potentielle."""
    # Basé sur:
    # - Capacité du canal
    # - Balance équilibré
    # - Connexion à pair actif
    
    capacity = int(channel.get("capacity", 0))
    local = int(channel.get("local_balance", 0))
    remote = int(channel.get("remote_balance", 0))
    total = local + remote
    
    if total == 0:
        return 30.0
    
    # Équilibre
    ratio = local / total
    balance_score = 100 - abs(ratio - 0.5) * 200  # Pénaliser déséquilibre
    
    # Capacité
    if capacity > 20_000_000:
        capacity_score = 100
    elif capacity > 5_000_000:
        capacity_score = 80
    elif capacity > 1_000_000:
        capacity_score = 60
    else:
        capacity_score = 40
    
    return (balance_score * 0.5 + capacity_score * 0.5)


def _calculate_redundancy_score(channel: Dict[str, Any], node_data: Dict[str, Any]) -> float:
    """Score de redondance (multiple paths)."""
    # Si le nœud a plusieurs canaux vers des pairs différents = bon
    # Si canal unique vers ce pair = moins de redondance
    
    peer_pubkey = channel.get("remote_pubkey")
    all_channels = node_data.get("channels", [])
    
    # Compter canaux vers le même pair
    channels_to_same_peer = len([
        c for c in all_channels 
        if c.get("remote_pubkey") == peer_pubkey
    ])
    
    if channels_to_same_peer > 1:
        # Multiple canaux vers même pair = redondance
        return 85.0
    
    # Sinon, regarder diversité globale
    unique_peers = len(set(c.get("remote_pubkey") for c in all_channels))
    
    if unique_peers > 20:
        return 90.0
    elif unique_peers > 10:
        return 75.0
    elif unique_peers > 5:
        return 65.0
    else:
        return 50.0


def get_network_position_components(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Composants détaillés."""
    return {
        "hub_vs_edge": _calculate_hub_score(channel, node_data, network_graph),
        "strategic": _calculate_strategic_score(channel, node_data),
        "routing_value": _calculate_routing_value_score(channel),
        "redundancy": _calculate_redundancy_score(channel, node_data),
        "num_channels": len(node_data.get("channels", [])),
        "position_type": _get_position_type(node_data)
    }


def _get_position_type(node_data: Dict[str, Any]) -> str:
    """Détermine le type de position."""
    num_channels = len(node_data.get("channels", []))
    
    if num_channels <= 5:
        return "Edge Node"
    elif num_channels <= 15:
        return "Intermediate Node"
    elif num_channels <= 50:
        return "Hub Node"
    else:
        return "Major Hub"

