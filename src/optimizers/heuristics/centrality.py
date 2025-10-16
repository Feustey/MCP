"""
Heuristique #1: Centrality Score

Évalue la position du nœud dans le réseau Lightning en utilisant :
- Betweenness Centrality : Nombre de plus courts chemins passant par ce nœud
- Closeness Centrality : Proximité moyenne aux autres nœuds
- Degree Centrality : Nombre de connexions
- Eigenvector Centrality : Qualité des connexions

Score: 0-100
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def calculate_centrality_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calcule le score de centralité pour un canal.
    
    Args:
        channel: Données du canal
        node_data: Données du nœud
        network_graph: Graphe du réseau (optionnel)
    
    Returns:
        Score entre 0 et 100
    """
    score = 0.0
    weights = {
        "betweenness": 0.35,
        "closeness": 0.25,
        "degree": 0.20,
        "eigenvector": 0.20
    }
    
    try:
        # 1. Betweenness Centrality (35%)
        betweenness = _calculate_betweenness(channel, node_data, network_graph)
        score += betweenness * weights["betweenness"]
        
        # 2. Closeness Centrality (25%)
        closeness = _calculate_closeness(channel, node_data, network_graph)
        score += closeness * weights["closeness"]
        
        # 3. Degree Centrality (20%)
        degree = _calculate_degree(channel, node_data)
        score += degree * weights["degree"]
        
        # 4. Eigenvector Centrality (20%)
        eigenvector = _calculate_eigenvector(channel, node_data, network_graph)
        score += eigenvector * weights["eigenvector"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Centrality = {score:.2f}")
        
    except Exception as e:
        logger.error(f"Erreur calcul centralité: {e}")
        score = 50.0  # Valeur neutre en cas d'erreur
    
    return min(100.0, max(0.0, score))


def _calculate_betweenness(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Optional[Dict[str, Any]]
) -> float:
    """
    Calcule le betweenness centrality (nombre de chemins passant par ce nœud).
    
    Returns:
        Score entre 0 et 100
    """
    if not network_graph:
        # Approximation basée sur les données locales
        num_channels = len(node_data.get("channels", []))
        total_capacity = sum(c.get("capacity", 0) for c in node_data.get("channels", []))
        
        # Normalisation : plus de canaux et de capacité = plus central
        channel_score = min(100, (num_channels / 50) * 100)  # 50 canaux = 100 points
        capacity_score = min(100, (total_capacity / 100_000_000) * 100)  # 1 BTC = 100 points
        
        return (channel_score * 0.6 + capacity_score * 0.4)
    
    # TODO: Calcul réel avec networkx si graph disponible
    # import networkx as nx
    # betweenness_dict = nx.betweenness_centrality(G)
    # return betweenness_dict[node_id] * 100
    
    return 50.0


def _calculate_closeness(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Optional[Dict[str, Any]]
) -> float:
    """
    Calcule le closeness centrality (proximité moyenne aux autres nœuds).
    
    Returns:
        Score entre 0 et 100
    """
    if not network_graph:
        # Approximation : nombre de canaux comme proxy de proximité
        num_channels = len(node_data.get("channels", []))
        
        # Plus de canaux = meilleure proximité (en moyenne)
        score = min(100, (num_channels / 30) * 100)  # 30 canaux = 100 points
        
        return score
    
    # TODO: Calcul réel avec networkx si graph disponible
    # import networkx as nx
    # closeness_dict = nx.closeness_centrality(G)
    # return closeness_dict[node_id] * 100
    
    return 50.0


def _calculate_degree(channel: Dict[str, Any], node_data: Dict[str, Any]) -> float:
    """
    Calcule le degree centrality (nombre de connexions).
    
    Returns:
        Score entre 0 et 100
    """
    num_channels = len(node_data.get("channels", []))
    
    # Normalisation : échelle logarithmique pour éviter trop de poids aux gros hubs
    # 1 canal = 10 points, 10 canaux = 50 points, 100 canaux = 100 points
    import math
    if num_channels == 0:
        return 0.0
    
    score = (math.log10(num_channels + 1) / math.log10(101)) * 100
    
    return min(100.0, score)


def _calculate_eigenvector(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Optional[Dict[str, Any]]
) -> float:
    """
    Calcule l'eigenvector centrality (qualité des connexions).
    
    Returns:
        Score entre 0 et 100
    """
    if not network_graph:
        # Approximation : capacité moyenne des canaux comme proxy
        channels = node_data.get("channels", [])
        if not channels:
            return 0.0
        
        avg_capacity = sum(c.get("capacity", 0) for c in channels) / len(channels)
        
        # Normalisation : 5M sats moyenne = 50 points, 20M+ = 100 points
        score = min(100, (avg_capacity / 20_000_000) * 100)
        
        return score
    
    # TODO: Calcul réel avec networkx si graph disponible
    # import networkx as nx
    # eigenvector_dict = nx.eigenvector_centrality(G, max_iter=100)
    # return eigenvector_dict[node_id] * 100
    
    return 50.0


def get_centrality_components(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_graph: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """
    Retourne les composants détaillés du score de centralité.
    
    Returns:
        Dict avec betweenness, closeness, degree, eigenvector
    """
    return {
        "betweenness": _calculate_betweenness(channel, node_data, network_graph),
        "closeness": _calculate_closeness(channel, node_data, network_graph),
        "degree": _calculate_degree(channel, node_data),
        "eigenvector": _calculate_eigenvector(channel, node_data, network_graph),
    }
