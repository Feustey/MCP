"""
Heuristique #4: Fee Competitiveness Score

Évalue la compétitivité des frais d'un canal par rapport au réseau :
- Comparaison avec la médiane du réseau
- Comparaison avec les pairs directs
- Ratio prix/performance
- Impact des frais sur le routing

Score: 0-100 (100 = frais très compétitifs)
"""

import logging
from typing import Dict, Any
import statistics

logger = logging.getLogger(__name__)

# Network defaults (seront remplacés par données réelles)
NETWORK_MEDIAN_BASE_FEE = 1000  # 1 sat
NETWORK_MEDIAN_FEE_RATE = 500  # 500 ppm


def calculate_competitiveness_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_stats: Dict[str, Any] = None,
    **kwargs
) -> float:
    """
    Calcule le score de compétitivité des frais.
    
    Args:
        channel: Données du canal
        node_data: Données du nœud
        network_stats: Statistiques du réseau (optionnel)
    
    Returns:
        Score entre 0 et 100
    """
    score = 0.0
    weights = {
        "vs_network": 0.40,
        "vs_peers": 0.30,
        "price_performance": 0.20,
        "routing_impact": 0.10
    }
    
    try:
        # 1. Vs Network Score (40%) - Comparaison avec réseau
        network_score = _calculate_vs_network_score(channel, network_stats)
        score += network_score * weights["vs_network"]
        
        # 2. Vs Peers Score (30%) - Comparaison avec pairs directs
        peers_score = _calculate_vs_peers_score(channel, node_data)
        score += peers_score * weights["vs_peers"]
        
        # 3. Price/Performance Score (20%) - Ratio qualité/prix
        perf_score = _calculate_price_performance_score(channel)
        score += perf_score * weights["price_performance"]
        
        # 4. Routing Impact Score (10%) - Impact sur routing
        routing_score = _calculate_routing_impact_score(channel)
        score += routing_score * weights["routing_impact"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Competitiveness = {score:.2f}")
        
    except Exception as e:
        logger.error(f"Erreur calcul compétitivité: {e}")
        score = 50.0
    
    return min(100.0, max(0.0, score))


def _calculate_vs_network_score(channel: Dict[str, Any], network_stats: Dict[str, Any] = None) -> float:
    """
    Compare les frais du canal avec la médiane du réseau.
    
    Returns:
        Score entre 0 et 100 (100 = frais très compétitifs)
    """
    policy = channel.get("policy", {})
    base_fee = int(policy.get("base_fee_msat", 1000))
    fee_rate = int(policy.get("fee_rate_ppm", 500))
    
    # Récupérer médianes réseau
    if network_stats:
        network_base = network_stats.get("median_base_fee", NETWORK_MEDIAN_BASE_FEE)
        network_rate = network_stats.get("median_fee_rate", NETWORK_MEDIAN_FEE_RATE)
    else:
        network_base = NETWORK_MEDIAN_BASE_FEE
        network_rate = NETWORK_MEDIAN_FEE_RATE
    
    # Calculer ratios
    base_ratio = base_fee / network_base if network_base > 0 else 1.0
    rate_ratio = fee_rate / network_rate if network_rate > 0 else 1.0
    
    # Score:
    # < 0.5x médiane = très compétitif (90-100 points)
    # 0.5-1.0x = compétitif (70-90 points)
    # 1.0-1.5x = dans la moyenne (50-70 points)
    # 1.5-2.0x = cher (30-50 points)
    # > 2.0x = très cher (0-30 points)
    
    avg_ratio = (base_ratio + rate_ratio) / 2
    
    if avg_ratio < 0.5:
        score = 90 + (0.5 - avg_ratio) * 20
    elif avg_ratio < 1.0:
        score = 70 + (1.0 - avg_ratio) * 40
    elif avg_ratio < 1.5:
        score = 50 + (1.5 - avg_ratio) * 40
    elif avg_ratio < 2.0:
        score = 30 + (2.0 - avg_ratio) * 40
    else:
        score = max(0, 30 - (avg_ratio - 2.0) * 15)
    
    return score


def _calculate_vs_peers_score(channel: Dict[str, Any], node_data: Dict[str, Any]) -> float:
    """
    Compare avec les frais des pairs directs (canaux similaires).
    
    Returns:
        Score entre 0 et 100
    """
    policy = channel.get("policy", {})
    my_fee_rate = int(policy.get("fee_rate_ppm", 500))
    
    # Récupérer les frais des autres canaux du nœud
    all_channels = node_data.get("channels", [])
    
    if len(all_channels) < 2:
        return 70.0  # Pas de comparaison possible
    
    # Extraire les fee_rate de tous les canaux
    peer_rates = []
    for ch in all_channels:
        if ch.get("channel_id") != channel.get("channel_id"):
            ch_policy = ch.get("policy", {})
            peer_rates.append(int(ch_policy.get("fee_rate_ppm", 500)))
    
    if not peer_rates:
        return 70.0
    
    # Calculer médiane et quartiles
    median_peer = statistics.median(peer_rates)
    
    # Comparer
    ratio = my_fee_rate / median_peer if median_peer > 0 else 1.0
    
    if ratio < 0.8:
        score = 85 + (0.8 - ratio) * 75
    elif ratio < 1.2:
        score = 85 - abs(ratio - 1.0) * 75
    elif ratio < 1.5:
        score = 60 - (ratio - 1.2) * 67
    else:
        score = max(0, 40 - (ratio - 1.5) * 40)
    
    return min(100.0, score)


def _calculate_price_performance_score(channel: Dict[str, Any]) -> float:
    """
    Évalue le ratio prix/performance.
    
    Returns:
        Score entre 0 et 100
    """
    policy = channel.get("policy", {})
    fee_rate = int(policy.get("fee_rate_ppm", 500))
    
    # Performance = success_rate * activity
    metrics = channel.get("metrics", {})
    activity_metrics = metrics.get("activity", {})
    
    success_rate = activity_metrics.get("success_rate", 0.75)
    forwards_count = activity_metrics.get("forwards_count", 0)
    
    # Performance normalisée (0-100)
    performance = (success_rate * 0.7 + min(1.0, forwards_count / 100) * 0.3) * 100
    
    # Ratio: performance élevée avec fee faible = bon
    if performance == 0:
        return 50.0
    
    # Fee normalisé (inverse: fee faible = score élevé)
    fee_normalized = max(0, 100 - (fee_rate / 50))  # 5000 ppm = 0 points
    
    # Score = moyenne pondérée
    score = (performance * 0.6 + fee_normalized * 0.4)
    
    return score


def _calculate_routing_impact_score(channel: Dict[str, Any]) -> float:
    """
    Évalue l'impact des frais sur le routing.
    
    Returns:
        Score entre 0 et 100
    """
    # Si les frais sont trop élevés, impact négatif sur le routing
    policy = channel.get("policy", {})
    fee_rate = int(policy.get("fee_rate_ppm", 500))
    
    # Récupérer l'activité
    forwards = channel.get("forwarding_history", [])
    
    # Si peu de forwards malgré bonne liquidité = probablement frais trop élevés
    capacity = int(channel.get("capacity", 0))
    
    if capacity == 0:
        return 50.0
    
    # Expected forwards basé sur capacité
    # Canal de 10M sats devrait avoir ~10 forwards/jour
    expected_forwards_per_month = (capacity / 1_000_000) * 30
    
    actual_forwards = len(forwards)
    
    ratio = actual_forwards / expected_forwards_per_month if expected_forwards_per_month > 0 else 0
    
    # Score basé sur ratio
    if ratio > 1.0:
        score = 100  # Dépasse les attentes
    elif ratio > 0.5:
        score = 70 + (ratio - 0.5) * 60
    elif ratio > 0.2:
        score = 40 + (ratio - 0.2) * 100
    else:
        score = ratio * 200
    
    return min(100.0, score)


def get_competitiveness_components(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    network_stats: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Retourne les composants détaillés du score de compétitivité.
    """
    policy = channel.get("policy", {})
    
    return {
        "vs_network": _calculate_vs_network_score(channel, network_stats),
        "vs_peers": _calculate_vs_peers_score(channel, node_data),
        "price_performance": _calculate_price_performance_score(channel),
        "routing_impact": _calculate_routing_impact_score(channel),
        "current_base_fee": policy.get("base_fee_msat", 0),
        "current_fee_rate": policy.get("fee_rate_ppm", 0),
        "network_median_rate": network_stats.get("median_fee_rate", NETWORK_MEDIAN_FEE_RATE) if network_stats else NETWORK_MEDIAN_FEE_RATE
    }


def suggest_fee_adjustment(channel: Dict[str, Any], node_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggère un ajustement de frais basé sur la compétitivité.
    
    Returns:
        Dict avec suggestion
    """
    score = calculate_competitiveness_score(channel, node_data)
    policy = channel.get("policy", {})
    current_rate = int(policy.get("fee_rate_ppm", 500))
    
    if score >= 70:
        return {
            "action": "maintain",
            "message": "Frais compétitifs, maintenir",
            "suggested_rate": current_rate
        }
    elif score >= 50:
        return {
            "action": "slight_decrease",
            "message": "Légère baisse recommandée pour plus de compétitivité",
            "suggested_rate": int(current_rate * 0.9)
        }
    else:
        return {
            "action": "decrease",
            "message": "Baisse significative recommandée - frais trop élevés",
            "suggested_rate": int(current_rate * 0.7)
        }
