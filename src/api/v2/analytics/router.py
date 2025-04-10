from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging
from .models import (
    FeeMarketMetric, FeeMarketAnalysis, FeeMarketAnalysisRequest,
    FeeMarketFilter, FeeMarketMetricType, FeeMarketTimeframe,
    FeeMarketSegment
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Création du routeur
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit"},
        404: {"description": "Ressource non trouvée"},
        500: {"description": "Erreur interne du serveur"}
    }
)

class AnalyticsDB:
    """Base de données en mémoire pour le service d'analyse"""
    def __init__(self):
        self.metrics: List[FeeMarketMetric] = []
        self.analyses: List[FeeMarketAnalysis] = []
        
        # Données de test
        self._init_test_data()
    
    def _init_test_data(self):
        """Initialisation des données de test"""
        # Métriques de test
        test_metric = FeeMarketMetric(
            id=str(uuid.uuid4()),
            type=FeeMarketMetricType.AVERAGE_FEE,
            value=0.0001,
            timestamp=datetime.utcnow(),
            timeframe=FeeMarketTimeframe.DAY,
            segment=FeeMarketSegment.RETAIL,
            channel_id="channel-456",
            node_id="node-789",
            metadata={"source": "lightning_network", "confidence": 0.95}
        )
        self.metrics.append(test_metric)
        
        # Analyse de test
        test_analysis = FeeMarketAnalysis(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            timeframe=FeeMarketTimeframe.DAY,
            segment=FeeMarketSegment.RETAIL,
            metrics=[test_metric],
            market_position=0.75,
            competitive_advantage=0.2,
            recommendations=[
                "Augmenter les frais de 10% pour le segment retail",
                "Maintenir les frais actuels pour le segment wholesale"
            ],
            confidence_score=0.85,
            metadata={"data_points": 1000, "market_volatility": "low"}
        )
        self.analyses.append(test_analysis)

# Instance de la base de données
db = AnalyticsDB()

@router.post("/metrics", response_model=FeeMarketMetric)
async def create_metric(metric: FeeMarketMetric):
    """Créer une nouvelle métrique de marché des frais"""
    try:
        metric.id = str(uuid.uuid4())
        db.metrics.append(metric)
        logger.info(f"Métrique créée avec succès: {metric.id}")
        return metric
    except Exception as e:
        logger.error(f"Erreur lors de la création de la métrique: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la métrique")

@router.get("/metrics", response_model=List[FeeMarketMetric])
async def list_metrics(
    filter: FeeMarketFilter = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Liste les métriques avec filtrage et pagination"""
    try:
        filtered_metrics = db.metrics
        
        # Application des filtres
        if filter.timeframe:
            filtered_metrics = [m for m in filtered_metrics if m.timeframe == filter.timeframe]
        if filter.segment:
            filtered_metrics = [m for m in filtered_metrics if m.segment == filter.segment]
        if filter.channel_id:
            filtered_metrics = [m for m in filtered_metrics if m.channel_id == filter.channel_id]
        if filter.node_id:
            filtered_metrics = [m for m in filtered_metrics if m.node_id == filter.node_id]
        if filter.start_date:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= filter.start_date]
        if filter.end_date:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp <= filter.end_date]
        
        # Pagination
        return filtered_metrics[skip:skip + limit]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques")

@router.get("/metrics/{metric_id}", response_model=FeeMarketMetric)
async def get_metric(metric_id: str):
    """Récupérer les détails d'une métrique spécifique"""
    try:
        metric = next((m for m in db.metrics if m.id == metric_id), None)
        if not metric:
            raise HTTPException(status_code=404, detail="Métrique non trouvée")
        return metric
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la métrique: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la métrique")

@router.post("/analyze", response_model=FeeMarketAnalysis)
async def analyze_market(request: FeeMarketAnalysisRequest):
    """Analyser le marché des frais"""
    try:
        # Récupération des métriques pertinentes
        relevant_metrics = [
            m for m in db.metrics
            if m.timeframe == request.timeframe
            and m.segment == request.segment
            and (not request.channel_id or m.channel_id == request.channel_id)
            and (not request.node_id or m.node_id == request.node_id)
        ]
        
        if not relevant_metrics:
            raise HTTPException(status_code=404, detail="Aucune métrique trouvée pour l'analyse")
        
        # Calcul des indicateurs de marché
        market_position = calculate_market_position(relevant_metrics)
        competitive_advantage = calculate_competitive_advantage(relevant_metrics)
        recommendations = generate_recommendations(relevant_metrics, market_position, competitive_advantage)
        
        # Création de l'analyse
        analysis = FeeMarketAnalysis(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            timeframe=request.timeframe,
            segment=request.segment,
            metrics=relevant_metrics,
            market_position=market_position,
            competitive_advantage=competitive_advantage,
            recommendations=recommendations,
            confidence_score=calculate_confidence_score(relevant_metrics),
            metadata={
                "data_points": len(relevant_metrics),
                "market_volatility": calculate_market_volatility(relevant_metrics),
                "include_competitors": request.include_competitors
            }
        )
        
        db.analyses.append(analysis)
        logger.info(f"Analyse créée avec succès: {analysis.id}")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du marché: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du marché")

@router.get("/analyze/{analysis_id}", response_model=FeeMarketAnalysis)
async def get_analysis(analysis_id: str):
    """Récupérer les détails d'une analyse spécifique"""
    try:
        analysis = next((a for a in db.analyses if a.id == analysis_id), None)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analyse non trouvée")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'analyse: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'analyse")

# Fonctions utilitaires pour l'analyse
def calculate_market_position(metrics: List[FeeMarketMetric]) -> float:
    """Calculer la position sur le marché (0-1)"""
    # Logique simplifiée pour l'exemple
    avg_fee = sum(m.value for m in metrics if m.type == FeeMarketMetricType.AVERAGE_FEE) / len(metrics)
    market_avg = 0.00015  # Valeur exemple
    return min(max((market_avg - avg_fee) / market_avg, 0), 1)

def calculate_competitive_advantage(metrics: List[FeeMarketMetric]) -> float:
    """Calculer l'avantage concurrentiel (-1 à 1)"""
    # Logique simplifiée pour l'exemple
    market_position = calculate_market_position(metrics)
    return (market_position - 0.5) * 2

def generate_recommendations(
    metrics: List[FeeMarketMetric],
    market_position: float,
    competitive_advantage: float
) -> List[str]:
    """Générer des recommandations basées sur l'analyse"""
    recommendations = []
    
    if market_position > 0.8:
        recommendations.append("Position de marché forte - Maintenir les frais actuels")
    elif market_position < 0.3:
        recommendations.append("Position de marché faible - Réduire les frais de 15%")
    
    if competitive_advantage > 0.5:
        recommendations.append("Fort avantage concurrentiel - Augmenter les frais de 10%")
    elif competitive_advantage < -0.5:
        recommendations.append("Désavantage concurrentiel - Réduire les frais de 20%")
    
    return recommendations

def calculate_confidence_score(metrics: List[FeeMarketMetric]) -> float:
    """Calculer le score de confiance de l'analyse (0-1)"""
    # Logique simplifiée pour l'exemple
    return min(len(metrics) / 100, 1.0)

def calculate_market_volatility(metrics: List[FeeMarketMetric]) -> str:
    """Calculer la volatilité du marché"""
    # Logique simplifiée pour l'exemple
    if len(metrics) < 10:
        return "unknown"
    
    values = [m.value for m in metrics]
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    
    if variance < 0.00001:
        return "low"
    elif variance < 0.0001:
        return "medium"
    else:
        return "high" 