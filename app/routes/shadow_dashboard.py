"""
Shadow Mode Dashboard - API endpoints pour visualisation Shadow Mode
Dernière mise à jour: 12 octobre 2025

Endpoints pour:
- Visualiser décisions shadow
- Comparer avec actions manuelles
- Analyser performance heuristiques
- Valider recommandations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

import structlog

from src.tools.shadow_mode_logger import ShadowModeLogger

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/shadow", tags=["Shadow Mode"])


# Instance globale (sera initialisée au démarrage)
shadow_logger: Optional[ShadowModeLogger] = None


def get_shadow_logger() -> ShadowModeLogger:
    """Récupère l'instance du shadow logger"""
    global shadow_logger
    if shadow_logger is None:
        shadow_logger = ShadowModeLogger(
            log_path="data/reports/shadow_mode",
            enable_daily_reports=True
        )
    return shadow_logger


@router.get("/status")
async def shadow_mode_status():
    """
    Retourne le status du mode shadow
    
    **Returns:**
    - Statut du shadow mode
    - Nombre de décisions loggées
    - Dernière décision
    """
    try:
        logger_instance = get_shadow_logger()
        
        # Statistiques des 7 derniers jours
        stats = await logger_instance.get_summary_stats(days=7)
        
        return {
            "status": "active",
            "enabled": True,
            "last_7_days": stats,
            "log_path": str(logger_instance.log_path),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("shadow_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions")
async def get_shadow_decisions(
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    decision_type: Optional[str] = Query(None, description="Type de décision")
):
    """
    Récupère les décisions shadow
    
    **Query Parameters:**
    - `date`: Date spécifique (défaut: aujourd'hui)
    - `limit`: Nombre max de résultats
    - `decision_type`: Filtrer par type
    
    **Returns:**
    - Liste des décisions shadow
    """
    try:
        logger_instance = get_shadow_logger()
        
        # Parse date
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()
        
        # Charger les logs
        logs = await logger_instance._load_logs_for_date(target_date)
        
        # Filtrer par type si demandé
        if decision_type:
            logs = [l for l in logs if l["decision"]["decision_type"] == decision_type]
        
        # Limiter
        logs = logs[:limit]
        
        return {
            "date": target_date.isoformat(),
            "count": len(logs),
            "decisions": logs
        }
        
    except Exception as e:
        logger.error("get_shadow_decisions_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{date}")
async def get_daily_report(date: str):
    """
    Récupère le rapport quotidien
    
    **Path Parameters:**
    - `date`: Date au format YYYY-MM-DD
    
    **Returns:**
    - Rapport quotidien complet
    """
    try:
        logger_instance = get_shadow_logger()
        
        # Parse date
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Charger ou générer le rapport
        report_path = logger_instance.log_path / f"daily_report_{date}.json"
        
        if report_path.exists():
            # Charger le rapport existant
            with open(report_path, 'r') as f:
                report = json.load(f)
        else:
            # Générer le rapport
            report = await logger_instance.generate_daily_report(report_date)
            
            if not report:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data available for {date}"
                )
        
        return report
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error("get_daily_report_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary(
    days: int = Query(7, ge=1, le=90, description="Nombre de jours")
):
    """
    Récupère un résumé sur plusieurs jours
    
    **Query Parameters:**
    - `days`: Nombre de jours à analyser (défaut: 7)
    
    **Returns:**
    - Statistiques agrégées
    - Trends
    - Recommandations globales
    """
    try:
        logger_instance = get_shadow_logger()
        
        summary = await logger_instance.get_summary_stats(days=days)
        
        # Ajouter quelques insights
        stats = summary.get("statistics", {})
        total = summary.get("total_decisions", 0)
        
        insights = []
        
        # Insight 1: Taux d'action
        decision_types = stats.get("decision_types", {})
        no_action_count = decision_types.get("no_action", 0)
        action_rate = (total - no_action_count) / total if total > 0 else 0
        
        if action_rate > 0.5:
            insights.append({
                "type": "warning",
                "message": f"{action_rate * 100:.0f}% des canaux nécessitent une action",
                "recommendation": "Système détecte beaucoup d'opportunités d'optimisation"
            })
        elif action_rate < 0.1:
            insights.append({
                "type": "success",
                "message": f"Seulement {action_rate * 100:.0f}% des canaux nécessitent une action",
                "recommendation": "Système semble bien calibré"
            })
        
        # Insight 2: Scores moyens
        avg_score = stats.get("average_score", 0)
        if avg_score < 0.5:
            insights.append({
                "type": "warning",
                "message": f"Score moyen faible ({avg_score:.2f})",
                "recommendation": "Beaucoup de canaux sous-optimaux"
            })
        elif avg_score > 0.8:
            insights.append({
                "type": "success",
                "message": f"Score moyen excellent ({avg_score:.2f})",
                "recommendation": "Canaux généralement bien optimisés"
            })
        
        summary["insights"] = insights
        summary["generated_at"] = datetime.now().isoformat()
        
        return summary
        
    except Exception as e:
        logger.error("get_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/{decision_id}")
async def validate_decision(
    decision_id: str,
    validation: Dict[str, Any]
):
    """
    Permet à un expert de valider une décision shadow
    
    **Path Parameters:**
    - `decision_id`: ID de la décision
    
    **Body:**
    ```json
    {
        "expert_agrees": true,
        "notes": "Décision sensée, aurait fait pareil",
        "expert_name": "John Doe"
    }
    ```
    
    **Returns:**
    - Confirmation de validation
    """
    try:
        # TODO: Charger la décision depuis storage
        # TODO: Ajouter la validation
        # TODO: Persister
        
        logger.info(
            "shadow_decision_validated",
            decision_id=decision_id,
            agrees=validation.get("expert_agrees")
        )
        
        return {
            "decision_id": decision_id,
            "validation_recorded": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("validate_decision_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_shadow_metrics():
    """
    Métriques de performance du shadow mode
    
    **Returns:**
    - Métriques de performance
    - Taux de validation experts
    - Accuracy des recommandations
    """
    try:
        logger_instance = get_shadow_logger()
        
        # Statistiques 30 jours
        stats_30d = await logger_instance.get_summary_stats(days=30)
        
        # TODO: Calculer métriques avancées
        # - Taux de validation experts
        # - Accuracy (si actions manuelles renseignées)
        # - False positives / false negatives
        
        metrics = {
            "period_days": 30,
            "total_decisions": stats_30d.get("total_decisions", 0),
            "average_score": stats_30d.get("statistics", {}).get("average_score", 0),
            "decision_breakdown": stats_30d.get("statistics", {}).get("decision_types", {}),
            # TODO: Ajouter métriques de validation
            "validation_rate": "N/A",  # % de décisions validées
            "agreement_rate": "N/A",   # % d'accord avec experts
            "generated_at": datetime.now().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error("get_shadow_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


import json  # Import manquant

