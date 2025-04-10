from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging
from .models import (
    LiquidityMetric, LiquidityMetricType, LiquidityMetricFilter,
    LiquidityThreshold, LiquidityThresholdCreate, LiquidityThresholdUpdate,
    LiquidityAlert, LiquidityAlertSeverity, LiquidityAlertFilter,
    LiquidityAnalysis, LiquidityAnalysisRequest
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du router
router = APIRouter(
    prefix="/liquidity",
    tags=["liquidité"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

# Base de données temporaire en mémoire (à remplacer par une vraie base de données)
class LiquidityDB:
    def __init__(self):
        self.metrics: Dict[str, LiquidityMetric] = {}
        self.thresholds: Dict[str, LiquidityThreshold] = {}
        self.alerts: Dict[str, LiquidityAlert] = {}
        self.analyses: Dict[str, LiquidityAnalysis] = {}

# Instance de la base de données
db = LiquidityDB()

# Routes pour la gestion des métriques
@router.post("/metrics", response_model=LiquidityMetric, status_code=status.HTTP_201_CREATED)
async def create_metric(metric: LiquidityMetric):
    """Créer une nouvelle métrique de liquidité"""
    metric_id = f"metric-{uuid.uuid4().hex[:8]}"
    metric.id = metric_id
    db.metrics[metric_id] = metric
    return metric

@router.get("/metrics", response_model=List[LiquidityMetric])
async def list_metrics(
    filter: LiquidityMetricFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les métriques de liquidité avec filtrage"""
    metrics = list(db.metrics.values())
    
    if filter.type:
        metrics = [m for m in metrics if m.type == filter.type]
    if filter.channel_id:
        metrics = [m for m in metrics if m.channel_id == filter.channel_id]
    if filter.node_id:
        metrics = [m for m in metrics if m.node_id == filter.node_id]
    if filter.start_time:
        metrics = [m for m in metrics if m.timestamp >= filter.start_time]
    if filter.end_time:
        metrics = [m for m in metrics if m.timestamp <= filter.end_time]
    
    return metrics[skip:skip + limit]

@router.get("/metrics/{metric_id}", response_model=LiquidityMetric)
async def get_metric(metric_id: str = Path(..., description="ID de la métrique")):
    """Obtenir les détails d'une métrique"""
    if metric_id not in db.metrics:
        raise HTTPException(status_code=404, detail="Métrique non trouvée")
    return db.metrics[metric_id]

# Routes pour la gestion des seuils
@router.post("/thresholds", response_model=LiquidityThreshold, status_code=status.HTTP_201_CREATED)
async def create_threshold(threshold: LiquidityThresholdCreate):
    """Créer un nouveau seuil de liquidité"""
    threshold_id = f"threshold-{uuid.uuid4().hex[:8]}"
    new_threshold = LiquidityThreshold(
        id=threshold_id,
        **threshold.dict(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.thresholds[threshold_id] = new_threshold
    return new_threshold

@router.get("/thresholds", response_model=List[LiquidityThreshold])
async def list_thresholds(
    channel_id: Optional[str] = None,
    node_id: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """Lister les seuils de liquidité avec filtrage"""
    thresholds = list(db.thresholds.values())
    
    if channel_id:
        thresholds = [t for t in thresholds if t.channel_id == channel_id]
    if node_id:
        thresholds = [t for t in thresholds if t.node_id == node_id]
    if is_active is not None:
        thresholds = [t for t in thresholds if t.is_active == is_active]
    
    return thresholds

@router.get("/thresholds/{threshold_id}", response_model=LiquidityThreshold)
async def get_threshold(threshold_id: str = Path(..., description="ID du seuil")):
    """Obtenir les détails d'un seuil"""
    if threshold_id not in db.thresholds:
        raise HTTPException(status_code=404, detail="Seuil non trouvé")
    return db.thresholds[threshold_id]

@router.put("/thresholds/{threshold_id}", response_model=LiquidityThreshold)
async def update_threshold(
    threshold_id: str = Path(..., description="ID du seuil"),
    threshold_update: LiquidityThresholdUpdate = None
):
    """Mettre à jour un seuil"""
    if threshold_id not in db.thresholds:
        raise HTTPException(status_code=404, detail="Seuil non trouvé")
    
    threshold = db.thresholds[threshold_id]
    update_data = threshold_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(threshold, field, value)
    threshold.updated_at = datetime.utcnow()
    
    return threshold

@router.delete("/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threshold(threshold_id: str = Path(..., description="ID du seuil")):
    """Supprimer un seuil"""
    if threshold_id not in db.thresholds:
        raise HTTPException(status_code=404, detail="Seuil non trouvé")
    del db.thresholds[threshold_id]

# Routes pour la gestion des alertes
@router.get("/alerts", response_model=List[LiquidityAlert])
async def list_alerts(
    filter: LiquidityAlertFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Lister les alertes de liquidité avec filtrage"""
    alerts = list(db.alerts.values())
    
    if filter.severity:
        alerts = [a for a in alerts if a.severity == filter.severity]
    if filter.is_acknowledged is not None:
        alerts = [a for a in alerts if a.is_acknowledged == filter.is_acknowledged]
    if filter.channel_id:
        alerts = [a for a in alerts if a.channel_id == filter.channel_id]
    if filter.node_id:
        alerts = [a for a in alerts if a.node_id == filter.node_id]
    if filter.start_time:
        alerts = [a for a in alerts if a.timestamp >= filter.start_time]
    if filter.end_time:
        alerts = [a for a in alerts if a.timestamp <= filter.end_time]
    
    return alerts[skip:skip + limit]

@router.get("/alerts/{alert_id}", response_model=LiquidityAlert)
async def get_alert(alert_id: str = Path(..., description="ID de l'alerte")):
    """Obtenir les détails d'une alerte"""
    if alert_id not in db.alerts:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    return db.alerts[alert_id]

@router.post("/alerts/{alert_id}/acknowledge", response_model=LiquidityAlert)
async def acknowledge_alert(
    alert_id: str = Path(..., description="ID de l'alerte"),
    user_id: str = Query(..., description="ID de l'utilisateur qui reconnaît l'alerte")
):
    """Reconnaître une alerte"""
    if alert_id not in db.alerts:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    alert = db.alerts[alert_id]
    alert.is_acknowledged = True
    alert.acknowledged_by = user_id
    alert.acknowledged_at = datetime.utcnow()
    
    return alert

# Routes pour l'analyse de liquidité
@router.post("/analyze", response_model=LiquidityAnalysis)
async def analyze_liquidity(request: LiquidityAnalysisRequest):
    """Analyser la liquidité d'un canal ou d'un nœud"""
    # Simulation d'une analyse de liquidité
    analysis_id = f"analysis-{uuid.uuid4().hex[:8]}"
    
    # Récupération des métriques pertinentes
    metrics = {}
    if request.channel_id:
        channel_metrics = [m for m in db.metrics.values() if m.channel_id == request.channel_id]
        for metric in channel_metrics:
            metrics[metric.type.value] = metric.value
    elif request.node_id:
        node_metrics = [m for m in db.metrics.values() if m.node_id == request.node_id]
        for metric in node_metrics:
            metrics[metric.type.value] = metric.value
    
    # Calcul du score et génération des recommandations
    score = calculate_liquidity_score(metrics)
    recommendations = []
    issues = []
    
    if request.include_recommendations:
        recommendations = generate_recommendations(metrics, score)
    if request.include_issues:
        issues = identify_issues(metrics, score)
    
    analysis = LiquidityAnalysis(
        id=analysis_id,
        channel_id=request.channel_id,
        node_id=request.node_id,
        timestamp=datetime.utcnow(),
        metrics=metrics,
        score=score,
        recommendations=recommendations,
        issues=issues,
        created_at=datetime.utcnow()
    )
    
    db.analyses[analysis_id] = analysis
    return analysis

@router.get("/analyze/{analysis_id}", response_model=LiquidityAnalysis)
async def get_analysis(analysis_id: str = Path(..., description="ID de l'analyse")):
    """Obtenir les détails d'une analyse"""
    if analysis_id not in db.analyses:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    return db.analyses[analysis_id]

# Fonctions utilitaires
def calculate_liquidity_score(metrics: Dict[str, float]) -> float:
    """Calculer un score de liquidité basé sur les métriques"""
    # Simulation d'un calcul de score
    score = 100.0
    
    if "channel_balance" in metrics:
        balance = metrics["channel_balance"]
        if balance < 100000:  # Moins de 0.001 BTC
            score -= 30
        elif balance < 500000:  # Moins de 0.005 BTC
            score -= 15
    
    if "payment_success" in metrics:
        success_rate = metrics["payment_success"]
        if success_rate < 0.95:
            score -= 20
        elif success_rate < 0.98:
            score -= 10
    
    if "fee_rate" in metrics:
        fee_rate = metrics["fee_rate"]
        if fee_rate > 0.001:
            score -= 15
        elif fee_rate > 0.0005:
            score -= 7
    
    return max(0.0, min(100.0, score))

def generate_recommendations(metrics: Dict[str, float], score: float) -> List[str]:
    """Générer des recommandations basées sur les métriques et le score"""
    recommendations = []
    
    if "channel_balance" in metrics:
        balance = metrics["channel_balance"]
        if balance < 100000:
            recommendations.append("Augmenter significativement la balance du canal (minimum 100,000 sats)")
        elif balance < 500000:
            recommendations.append("Augmenter la balance du canal pour plus de liquidité")
    
    if "payment_success" in metrics:
        success_rate = metrics["payment_success"]
        if success_rate < 0.95:
            recommendations.append("Améliorer le taux de succès des paiements en optimisant les routes")
        elif success_rate < 0.98:
            recommendations.append("Vérifier les routes de paiement pour améliorer le taux de succès")
    
    if "fee_rate" in metrics:
        fee_rate = metrics["fee_rate"]
        if fee_rate > 0.001:
            recommendations.append("Réduire significativement les frais de routage")
        elif fee_rate > 0.0005:
            recommendations.append("Optimiser les frais de routage pour plus de compétitivité")
    
    return recommendations

def identify_issues(metrics: Dict[str, float], score: float) -> List[str]:
    """Identifier les problèmes basés sur les métriques et le score"""
    issues = []
    
    if score < 50:
        issues.append("État critique de la liquidité")
    elif score < 70:
        issues.append("État préoccupant de la liquidité")
    elif score < 85:
        issues.append("État sous-optimal de la liquidité")
    
    if "channel_balance" in metrics:
        balance = metrics["channel_balance"]
        if balance < 100000:
            issues.append("Balance du canal insuffisante")
        elif balance < 500000:
            issues.append("Balance du canal faible")
    
    if "payment_success" in metrics:
        success_rate = metrics["payment_success"]
        if success_rate < 0.95:
            issues.append("Taux de succès des paiements très bas")
        elif success_rate < 0.98:
            issues.append("Taux de succès des paiements sous-optimal")
    
    if "fee_rate" in metrics:
        fee_rate = metrics["fee_rate"]
        if fee_rate > 0.001:
            issues.append("Frais de routage trop élevés")
        elif fee_rate > 0.0005:
            issues.append("Frais de routage élevés")
    
    return issues 