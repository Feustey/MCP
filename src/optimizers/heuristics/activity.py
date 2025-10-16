"""
Heuristique #3: Forward Activity Score

Évalue l'activité de forwarding d'un canal :
- Nombre de forwards (volume)
- Taux de succès des forwards
- Volume total routé
- Fees générés
- Tendance d'activité (croissante/décroissante)

Score: 0-100 (100 = très actif et performant)
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Thresholds
MIN_FORWARDS_PER_DAY = 10  # Pour score optimal
MIN_SUCCESS_RATE = 0.85  # 85% minimum pour score élevé
MIN_VOLUME_SATS = 1_000_000  # 1M sats/jour pour score optimal


def calculate_activity_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    **kwargs
) -> float:
    """
    Calcule le score d'activité de forwarding pour un canal.
    
    Args:
        channel: Données du canal
        node_data: Données du nœud
    
    Returns:
        Score entre 0 et 100
    """
    score = 0.0
    weights = {
        "volume": 0.30,
        "frequency": 0.25,
        "success_rate": 0.25,
        "revenue": 0.15,
        "trend": 0.05
    }
    
    try:
        # 1. Volume Score (30%) - Volume total routé
        volume_score = _calculate_volume_score(channel)
        score += volume_score * weights["volume"]
        
        # 2. Frequency Score (25%) - Nombre de forwards
        frequency_score = _calculate_frequency_score(channel)
        score += frequency_score * weights["frequency"]
        
        # 3. Success Rate Score (25%) - Taux de succès
        success_score = _calculate_success_rate_score(channel)
        score += success_score * weights["success_rate"]
        
        # 4. Revenue Score (15%) - Fees générés
        revenue_score = _calculate_revenue_score(channel)
        score += revenue_score * weights["revenue"]
        
        # 5. Trend Score (5%) - Tendance
        trend_score = _calculate_trend_score(channel)
        score += trend_score * weights["trend"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Activity = {score:.2f}")
        
    except Exception as e:
        logger.error(f"Erreur calcul activité: {e}")
        score = 30.0  # Valeur basse par défaut (inactif jusqu'à preuve du contraire)
    
    return min(100.0, max(0.0, score))


def _calculate_volume_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de volume routé.
    
    Returns:
        Score entre 0 et 100
    """
    # Récupérer historique forwards
    forwards = channel.get("forwarding_history", [])
    
    if not forwards:
        return 0.0
    
    # Volume total sur 30 jours (en sats)
    total_volume = sum(f.get("amt_out", 0) for f in forwards)
    
    # Volume quotidien moyen
    avg_daily_volume = total_volume / 30 if len(forwards) > 0 else 0
    
    # Normalisation : 1M sats/jour = 60 points, 10M+ = 100 points
    import math
    if avg_daily_volume < 1000:
        score = 0.0
    else:
        normalized = (math.log10(avg_daily_volume) - math.log10(1000)) / \
                     (math.log10(10_000_000) - math.log10(1000))
        score = 60 + (normalized * 40)
    
    return min(100.0, max(0.0, score))


def _calculate_frequency_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de fréquence des forwards.
    
    Returns:
        Score entre 0 et 100
    """
    forwards = channel.get("forwarding_history", [])
    
    if not forwards:
        return 0.0
    
    # Nombre de forwards sur 30 jours
    num_forwards = len(forwards)
    
    # Forwards par jour en moyenne
    avg_per_day = num_forwards / 30
    
    # Normalisation : 10/jour = 70 points, 50+/jour = 100 points
    if avg_per_day < 1:
        score = avg_per_day * 30  # 1/jour = 30 points
    elif avg_per_day < MIN_FORWARDS_PER_DAY:
        score = 30 + ((avg_per_day - 1) / 9) * 40  # 1-10 = 30-70 points
    else:
        excess = min(40, (avg_per_day - MIN_FORWARDS_PER_DAY) / 40)
        score = 70 + (excess * 30)  # 10-50 = 70-100 points
    
    return min(100.0, score)


def _calculate_success_rate_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de taux de succès.
    
    Returns:
        Score entre 0 et 100
    """
    metrics = channel.get("metrics", {})
    activity = metrics.get("activity", {})
    
    success_rate = activity.get("success_rate", 0.0)
    
    if success_rate == 0.0:
        # Pas de données, vérifier les forwards
        forwards = channel.get("forwarding_history", [])
        if forwards:
            successful = len([f for f in forwards if f.get("success", True)])
            success_rate = successful / len(forwards)
        else:
            return 50.0  # Valeur neutre si pas de données
    
    # Conversion en score:
    # < 70% = mauvais (0-40 points)
    # 70-85% = moyen (40-70 points)
    # 85-95% = bon (70-90 points)
    # 95%+ = excellent (90-100 points)
    
    if success_rate < 0.70:
        score = success_rate / 0.70 * 40
    elif success_rate < MIN_SUCCESS_RATE:
        score = 40 + ((success_rate - 0.70) / 0.15) * 30
    elif success_rate < 0.95:
        score = 70 + ((success_rate - MIN_SUCCESS_RATE) / 0.10) * 20
    else:
        score = 90 + ((success_rate - 0.95) / 0.05) * 10
    
    return min(100.0, score)


def _calculate_revenue_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de revenue (fees générés).
    
    Returns:
        Score entre 0 et 100
    """
    forwards = channel.get("forwarding_history", [])
    
    if not forwards:
        return 0.0
    
    # Fees totaux sur 30 jours (en sats)
    total_fees = sum(f.get("fee", 0) for f in forwards)
    
    # Fees par jour
    daily_fees = total_fees / 30
    
    # Normalisation : 100 sats/jour = 50 points, 1000+ sats/jour = 100 points
    import math
    if daily_fees < 10:
        score = daily_fees * 2  # 10 sats = 20 points
    elif daily_fees < 100:
        score = 20 + ((math.log10(daily_fees) - 1) / 1) * 30  # 10-100 = 20-50 points
    else:
        score = 50 + (min(1, (math.log10(daily_fees) - 2) / 1) * 50)  # 100-1000+ = 50-100 points
    
    return min(100.0, score)


def _calculate_trend_score(channel: Dict[str, Any]) -> float:
    """
    Calcule le score de tendance d'activité.
    
    Returns:
        Score entre 0 et 100 (100 = tendance croissante forte)
    """
    forwards = channel.get("forwarding_history", [])
    
    if len(forwards) < 7:  # Besoin d'au moins 7 jours
        return 50.0  # Neutre
    
    # Diviser en 2 périodes : première moitié vs seconde moitié
    mid = len(forwards) // 2
    first_half = forwards[:mid]
    second_half = forwards[mid:]
    
    vol_first = sum(f.get("amt_out", 0) for f in first_half)
    vol_second = sum(f.get("amt_out", 0) for f in second_half)
    
    if vol_first == 0:
        return 50.0 if vol_second == 0 else 80.0
    
    # Ratio de croissance
    growth_ratio = vol_second / vol_first
    
    # Conversion en score:
    # < 0.5 = déclin fort (0 points)
    # 0.5-0.9 = déclin (20-45 points)
    # 0.9-1.1 = stable (45-55 points)
    # 1.1-2.0 = croissance (55-80 points)
    # > 2.0 = forte croissance (80-100 points)
    
    if growth_ratio < 0.5:
        score = growth_ratio * 40
    elif growth_ratio < 0.9:
        score = 20 + ((growth_ratio - 0.5) / 0.4) * 25
    elif growth_ratio < 1.1:
        score = 45 + ((growth_ratio - 0.9) / 0.2) * 10
    elif growth_ratio < 2.0:
        score = 55 + ((growth_ratio - 1.1) / 0.9) * 25
    else:
        score = 80 + min(20, (growth_ratio - 2.0) * 10)
    
    return min(100.0, max(0.0, score))


def get_activity_components(channel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retourne les composants détaillés du score d'activité.
    
    Returns:
        Dict avec tous les composants
    """
    forwards = channel.get("forwarding_history", [])
    
    return {
        "volume": _calculate_volume_score(channel),
        "frequency": _calculate_frequency_score(channel),
        "success_rate": _calculate_success_rate_score(channel),
        "revenue": _calculate_revenue_score(channel),
        "trend": _calculate_trend_score(channel),
        "total_forwards": len(forwards),
        "total_volume_sats": sum(f.get("amt_out", 0) for f in forwards),
        "total_fees_sats": sum(f.get("fee", 0) for f in forwards),
    }


def is_channel_active(channel: Dict[str, Any], threshold: float = 30.0) -> bool:
    """
    Détermine si un canal est considéré comme actif.
    
    Args:
        channel: Données du canal
        threshold: Seuil de score minimum pour être considéré actif
    
    Returns:
        True si actif
    """
    score = calculate_activity_score(channel, {})
    return score >= threshold
