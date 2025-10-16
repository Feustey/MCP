"""
Heuristique #6: Age & Stability Score

Évalue l'ancienneté et la stabilité du canal :
- Âge du canal
- Stabilité de la capacité
- Historique de mises à jour policy
- Longévité projetée

Score: 0-100 (100 = canal ancien et stable)
"""

import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_age_stability_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    **kwargs
) -> float:
    """Calcule le score d'âge et stabilité."""
    score = 0.0
    weights = {
        "age": 0.40,
        "capacity_stability": 0.35,
        "policy_stability": 0.25
    }
    
    try:
        score += _calculate_age_score(channel) * weights["age"]
        score += _calculate_capacity_stability_score(channel) * weights["capacity_stability"]
        score += _calculate_policy_stability_score(channel) * weights["policy_stability"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Age/Stability = {score:.2f}")
    except Exception as e:
        logger.error(f"Erreur calcul age/stability: {e}")
        score = 60.0
    
    return min(100.0, max(0.0, score))


def _calculate_age_score(channel: Dict[str, Any]) -> float:
    """Score basé sur l'âge du canal."""
    created_at = channel.get("created_at")
    if not created_at:
        return 50.0
    
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            return 50.0
    
    age_days = (datetime.now() - created_at).days
    
    # Échelle logarithmique
    # < 7 jours = nouveau (20-40)
    # 7-30 jours = récent (40-60)
    # 30-90 jours = établi (60-75)
    # 90-180 jours = mature (75-85)
    # 180-365 jours = ancien (85-95)
    # > 365 jours = très ancien (95-100)
    
    if age_days < 7:
        return 20 + (age_days / 7) * 20
    elif age_days < 30:
        return 40 + ((age_days - 7) / 23) * 20
    elif age_days < 90:
        return 60 + ((age_days - 30) / 60) * 15
    elif age_days < 180:
        return 75 + ((age_days - 90) / 90) * 10
    elif age_days < 365:
        return 85 + ((age_days - 180) / 185) * 10
    else:
        return min(100, 95 + ((age_days - 365) / 365) * 5)


def _calculate_capacity_stability_score(channel: Dict[str, Any]) -> float:
    """Score de stabilité de la capacité (pas de changements fréquents)."""
    capacity_changes = channel.get("capacity_change_count", 0)
    
    # Moins de changements = plus stable
    if capacity_changes == 0:
        return 100.0
    elif capacity_changes <= 1:
        return 90.0
    elif capacity_changes <= 3:
        return 75.0
    else:
        return max(40.0, 75 - (capacity_changes - 3) * 10)


def _calculate_policy_stability_score(channel: Dict[str, Any]) -> float:
    """Score de stabilité des policies (pas de changements fréquents)."""
    policy_changes = channel.get("policy_change_count", 0)
    
    # Changements modérés = bon (trop peu ou trop = mauvais)
    if policy_changes == 0:
        return 60.0  # Pas de changement peut être mauvais (pas d'optimisation)
    elif policy_changes <= 3:
        return 85.0
    elif policy_changes <= 10:
        return 100.0  # Optimisation active
    elif policy_changes <= 20:
        return 85.0
    else:
        return max(50.0, 85 - (policy_changes - 20) * 2)  # Trop de changements = instable


def get_age_stability_components(channel: Dict[str, Any]) -> Dict[str, Any]:
    """Composants détaillés."""
    created_at = channel.get("created_at")
    age_days = 0
    
    if created_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                pass
        
        if isinstance(created_at, datetime):
            age_days = (datetime.now() - created_at).days
    
    return {
        "age": _calculate_age_score(channel),
        "capacity_stability": _calculate_capacity_stability_score(channel),
        "policy_stability": _calculate_policy_stability_score(channel),
        "age_days": age_days,
        "capacity_changes": channel.get("capacity_change_count", 0),
        "policy_changes": channel.get("policy_change_count", 0)
    }

