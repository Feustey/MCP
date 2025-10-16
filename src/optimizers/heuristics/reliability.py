"""
Heuristique #5: Uptime & Reliability Score

Évalue la fiabilité du pair :
- Uptime du nœud pair
- Historique de déconnexions
- Stabilité de la connexion
- Réactivité

Score: 0-100 (100 = très fiable, toujours en ligne)
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_reliability_score(
    channel: Dict[str, Any],
    node_data: Dict[str, Any],
    **kwargs
) -> float:
    """Calcule le score de fiabilité."""
    score = 0.0
    weights = {
        "uptime": 0.50,
        "stability": 0.30,
        "history": 0.20
    }
    
    try:
        score += _calculate_uptime_score(channel) * weights["uptime"]
        score += _calculate_stability_score(channel) * weights["stability"]
        score += _calculate_history_score(channel) * weights["history"]
        
        logger.debug(f"Canal {channel.get('channel_id', 'unknown')[:8]}: Reliability = {score:.2f}")
    except Exception as e:
        logger.error(f"Erreur calcul fiabilité: {e}")
        score = 75.0  # Valeur par défaut optimiste
    
    return min(100.0, max(0.0, score))


def _calculate_uptime_score(channel: Dict[str, Any]) -> float:
    """Score d'uptime actuel."""
    peer_uptime = channel.get("peer_uptime", 0.95)  # 95% par défaut
    return peer_uptime * 100


def _calculate_stability_score(channel: Dict[str, Any]) -> float:
    """Score de stabilité de connexion."""
    disconnections = channel.get("disconnection_count", 0)
    
    # Score basé sur nombre de déconnexions (30 derniers jours)
    if disconnections == 0:
        return 100.0
    elif disconnections <= 2:
        return 90.0
    elif disconnections <= 5:
        return 75.0
    elif disconnections <= 10:
        return 60.0
    else:
        return max(20.0, 60 - (disconnections - 10) * 4)


def _calculate_history_score(channel: Dict[str, Any]) -> float:
    """Score basé sur l'historique."""
    # Durée depuis création du canal
    created_at = channel.get("created_at")
    if not created_at:
        return 70.0
    
    # Si string, convertir
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            return 70.0
    
    age_days = (datetime.now() - created_at).days
    
    # Plus ancien = plus fiable historiquement
    if age_days > 365:
        return 100.0
    elif age_days > 180:
        return 90.0
    elif age_days > 90:
        return 80.0
    elif age_days > 30:
        return 70.0
    else:
        return max(50.0, 50 + (age_days / 30) * 20)


def get_reliability_components(channel: Dict[str, Any]) -> Dict[str, float]:
    """Composants détaillés."""
    return {
        "uptime": _calculate_uptime_score(channel),
        "stability": _calculate_stability_score(channel),
        "history": _calculate_history_score(channel),
        "peer_uptime_pct": channel.get("peer_uptime", 0.95) * 100,
        "disconnections": channel.get("disconnection_count", 0)
    }
