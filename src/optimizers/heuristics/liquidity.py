"""
Heuristique #2: Liquidity Balance Score

Évalue l'équilibre de liquidité d'un canal :
- Ratio local/remote optimal (0.5)
- Capacité totale du canal
- Liquidité disponible pour forwards
- Historique de déséquilibres

Score: 0-100 (100 = parfaitement équilibré avec bonne capacité)
"""

import logging
from typing import Dict, Any
import math

logger = logging.getLogger(__name__)

# Thresholds
OPTIMAL_RATIO = 0.5  # Ratio idéal local/remote
RATIO_TOLERANCE = 0.15  # Tolérance (0.35 - 0.65 = bon)
MIN_CAPACITY_SATS = 1_000_000  # 1M sats minimum pour score optimal


def calculate_liquidity_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    **kwargs
) -> float:
    """
    Calcule le score de liquidité pour un canal.
    
    Args:
        channel: Données du canal
        node_data: Données du nœud
    
    Returns:
        Score entre 0 et 100
    """
    score = 0.0
    weights = {
        "balance": 0.40,
        "capacity": 0.30,
        "available": 0.20,
        "volatility": 0.10
    }
    
    try:
        # 1. Balance Score (40%) - Équilibre local/remote
        balance_score = _calculate_balance_score(channel)
        score += balance_score * weights["balance"]
        
        # 2. Capacity Score (30%) - Capacité totale
        capacity_score = _calculate_capacity_score(channel)
        score += capacity_score * weights["capacity"]
        
        # 3. Available Score (20%) - Liquidité disponible
        available_score = _calculate_available_score(channel)
        score += available_score * weights["available"]
        
        # 4. Volatility Score (10%) - Stabilité du ratio
        volatility_score = _calculate_volatility_score(channel)
        score += volatility_score * weights["volatility"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Liquidity = {score:.2f}")
        
    except Exception as e:
        logger.error(f"Erreur calcul liquidité: {e}")
        score = 50.0
    
    return min(100.0, max(0.0, score))


def _calculate_balance_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score d'équilibre local/remote.
    
    Returns:
        Score entre 0 et 100 (100 = parfaitement équilibré)
    """
    local_balance = int(channel.get("local_balance", 0))
    remote_balance = int(channel.get("remote_balance", 0))
    total_balance = local_balance + remote_balance
    
    if total_balance == 0:
        return 0.0
    
    ratio = local_balance / total_balance
    
    # Distance à l'optimal
    deviation = abs(ratio - OPTIMAL_RATIO)
    
    # Score: 100 si ratio = 0.5, décroît avec la déviation
    if deviation <= RATIO_TOLERANCE:
        # Dans la zone acceptable: score élevé
        score = 100 - (deviation / RATIO_TOLERANCE) * 20  # Max -20 points
    else:
        # Hors zone acceptable: pénalité plus forte
        excess_deviation = deviation - RATIO_TOLERANCE
        score = 80 - (excess_deviation / (0.5 - RATIO_TOLERANCE)) * 80
    
    return max(0.0, score)


def _calculate_capacity_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de capacité totale.
    
    Returns:
        Score entre 0 et 100
    """
    capacity = int(channel.get("capacity", 0))
    
    if capacity == 0:
        return 0.0
    
    # Échelle logarithmique pour éviter trop de poids aux gros canaux
    # 1M sats = 50 points, 5M = 75 points, 20M+ = 100 points
    normalized = (math.log10(capacity + 1) - math.log10(MIN_CAPACITY_SATS)) / \
                 (math.log10(20_000_000) - math.log10(MIN_CAPACITY_SATS))
    
    score = normalized * 100
    
    return min(100.0, max(0.0, score))


def _calculate_available_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de liquidité disponible pour forwards.
    
    Returns:
        Score entre 0 et 100
    """
    local_balance = int(channel.get("local_balance", 0))
    remote_balance = int(channel.get("remote_balance", 0))
    capacity = int(channel.get("capacity", 0))
    
    if capacity == 0:
        return 0.0
    
    # Liquidité disponible pour routing = min(local, remote)
    # Un canal avec 10M local et 10k remote a peu de liquidité utile
    available = min(local_balance, remote_balance)
    
    # Score basé sur le % de capacité utilisable
    ratio = (available * 2) / capacity  # *2 car min() donne max 50%
    
    score = ratio * 100
    
    return min(100.0, score)


def _calculate_volatility_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de volatilité (stabilité du ratio over time).
    
    Returns:
        Score entre 0 et 100 (100 = très stable)
    """
    # TODO: Implémenter avec historique réel
    # Pour l'instant, retourner score neutre
    
    # Si historique disponible:
    # history = channel.get("balance_history", [])
    # if history:
    #     ratios = [h["local"] / (h["local"] + h["remote"]) for h in history]
    #     std_dev = np.std(ratios)
    #     score = max(0, 100 - (std_dev * 500))  # Pénaliser la volatilité
    #     return score
    
    return 70.0  # Valeur par défaut


def get_liquidity_components(channel: Dict[str, Any]) -> Dict[str, float]:
    """
    Retourne les composants détaillés du score de liquidité.
    
    Returns:
        Dict avec balance, capacity, available, volatility
    """
    return {
        "balance": _calculate_balance_score(channel),
        "capacity": _calculate_capacity_score(channel),
        "available": _calculate_available_score(channel),
        "volatility": _calculate_volatility_score(channel),
        "ratio": _get_current_ratio(channel),
        "deviation_from_optimal": abs(_get_current_ratio(channel) - OPTIMAL_RATIO)
    }


def _get_current_ratio(channel: Dict[str, Any]) -> float:
    """Calcule le ratio local/(local+remote) actuel."""
    local = int(channel.get("local_balance", 0))
    remote = int(channel.get("remote_balance", 0))
    total = local + remote
    
    return local / total if total > 0 else 0.5


def get_balance_recommendation(channel: Dict[str, Any]) -> str:
    """
    Retourne une recommandation textuelle pour le canal.
    
    Returns:
        Recommandation en texte clair
    """
    ratio = _get_current_ratio(channel)
    deviation = abs(ratio - OPTIMAL_RATIO)
    
    if deviation <= RATIO_TOLERANCE:
        return "✅ Équilibré - Aucune action nécessaire"
    elif ratio > 0.65:
        return f"⚠️ Trop de liquidité locale ({ratio*100:.0f}%) - Considérer rebalance ou baisse de fees"
    elif ratio < 0.35:
        return f"⚠️ Trop de liquidité remote ({(1-ratio)*100:.0f}%) - Considérer augmentation fees ou rebalance"
    else:
        return "ℹ️ Légèrement déséquilibré - Surveillance recommandée"
