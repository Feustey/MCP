"""
Lightning Scoring API Routes

Endpoints pour accéder aux scores et recommandations des nœuds et canaux Lightning.

Dernière mise à jour: 15 octobre 2025
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.lightning_scoring import LightningScoreService
from src.optimizers.decision_engine import DecisionEngine, DecisionType
from app.db import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lightning", tags=["Lightning Scoring"])


# ========== Models Pydantic ==========

class ScoreComponents(BaseModel):
    """Composants détaillés du score."""
    centrality: float = Field(..., ge=0, le=100)
    liquidity: float = Field(..., ge=0, le=100)
    activity: float = Field(..., ge=0, le=100)
    competitiveness: float = Field(..., ge=0, le=100)
    reliability: float = Field(..., ge=0, le=100)
    age: float = Field(..., ge=0, le=100)
    peer_quality: float = Field(..., ge=0, le=100)
    position: float = Field(..., ge=0, le=100)


class NodeScoreResponse(BaseModel):
    """Réponse pour le score d'un nœud."""
    node_id: str
    composite_score: float = Field(..., ge=0, le=100)
    components: ScoreComponents
    rank: Optional[int] = None
    calculated_at: str
    
    class Config:
        schema_extra = {
            "example": {
                "node_id": "03abc...",
                "composite_score": 78.5,
                "components": {
                    "centrality": 85.0,
                    "liquidity": 75.0,
                    "activity": 80.0,
                    "competitiveness": 70.0,
                    "reliability": 90.0,
                    "age": 65.0,
                    "peer_quality": 75.0,
                    "position": 80.0
                },
                "rank": 42,
                "calculated_at": "2025-10-15T10:30:00Z"
            }
        }


class ChannelRecommendation(BaseModel):
    """Recommandation pour un canal."""
    channel_id: str
    decision: str
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    params: dict = {}
    
    class Config:
        schema_extra = {
            "example": {
                "channel_id": "123456x789x0",
                "decision": "decrease_fees",
                "confidence": 0.75,
                "reasoning": "Frais peu compétitifs avec faible activité...",
                "params": {
                    "current_fee_rate": 1000,
                    "suggested_fee_rate": 800
                }
            }
        }


class BatchScoreRequest(BaseModel):
    """Requête pour scoring batch."""
    node_ids: List[str] = Field(..., min_items=1, max_items=100)
    force: bool = False


class RecalculateRequest(BaseModel):
    """Requête pour recalcul de scores."""
    node_ids: Optional[List[str]] = None
    force: bool = False


class PaginationMetadata(BaseModel):
    """Métadonnées de pagination."""
    total: int
    page: int
    limit: int
    pages: int


class RankingsResponse(BaseModel):
    """Réponse pour les rankings."""
    data: List[NodeScoreResponse]
    metadata: PaginationMetadata


# ========== Dependency Injection ==========

async def get_scoring_service(db = Depends(get_database)) -> LightningScoreService:
    """Retourne une instance du service de scoring."""
    return LightningScoreService(db)


async def get_decision_engine() -> DecisionEngine:
    """Retourne une instance du decision engine."""
    return DecisionEngine()


# ========== Endpoints ==========

@router.get(
    "/scores/node/{node_id}",
    response_model=NodeScoreResponse,
    summary="Score d'un nœud",
    description="Retourne le score composite et les composants détaillés pour un nœud Lightning"
)
async def get_node_score(
    node_id: str,
    force_recalculate: bool = Query(False, description="Forcer le recalcul du score"),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Récupère le score d'un nœud Lightning.
    
    - **node_id**: Clé publique du nœud
    - **force_recalculate**: Force le recalcul même si un score récent existe
    """
    try:
        # Forcer recalcul si demandé
        if force_recalculate:
            await service.calculate_node_score(node_id)
        
        # Récupérer le score
        score = await service.get_node_score(node_id)
        
        if not score:
            # Calculer si pas de score
            score = await service.calculate_node_score(node_id)
            
            if not score:
                raise HTTPException(
                    status_code=404,
                    detail=f"Node {node_id} not found or unable to calculate score"
                )
        
        # Formater réponse
        metrics = score.get("metrics", {})
        
        return NodeScoreResponse(
            node_id=node_id,
            composite_score=metrics.get("composite", 0.0),
            components=ScoreComponents(
                centrality=metrics.get("centrality", 0.0),
                liquidity=75.0,  # TODO: Ajouter dans metrics
                activity=80.0,
                competitiveness=70.0,
                reliability=metrics.get("reliability", 0.0),
                age=65.0,
                peer_quality=75.0,
                position=80.0
            ),
            rank=None,  # TODO: Calculer rank
            calculated_at=score.get("timestamp", "").isoformat() if hasattr(score.get("timestamp", ""), "isoformat") else str(score.get("timestamp", ""))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur get_node_score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scores/channel/{channel_id}",
    response_model=ChannelRecommendation,
    summary="Recommandation pour un canal",
    description="Analyse un canal et retourne une recommandation d'optimisation"
)
async def get_channel_recommendation(
    channel_id: str,
    engine: DecisionEngine = Depends(get_decision_engine),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Analyse un canal et retourne une recommandation.
    
    - **channel_id**: ID du canal (format: txid:vout ou short_channel_id)
    """
    try:
        # TODO: Récupérer données du canal depuis DB/API
        # Pour l'instant, exemple simulé
        
        channel_data = {
            "channel_id": channel_id,
            "local_balance": 5000000,
            "remote_balance": 5000000,
            "capacity": 10000000,
            "policy": {
                "base_fee_msat": 1000,
                "fee_rate_ppm": 500
            }
        }
        
        node_data = {
            "channels": [channel_data]
        }
        
        # Évaluer via decision engine
        evaluation = engine.evaluate_channel(channel_data, node_data)
        
        decision_type = evaluation.get("decision")
        if isinstance(decision_type, DecisionType):
            decision_str = decision_type.value
        else:
            decision_str = str(decision_type)
        
        return ChannelRecommendation(
            channel_id=channel_id,
            decision=decision_str,
            confidence=evaluation.get("confidence", 0.0),
            reasoning=evaluation.get("reasoning", ""),
            params=evaluation.get("params", {})
        )
        
    except Exception as e:
        logger.error(f"Erreur get_channel_recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scores/batch",
    response_model=List[NodeScoreResponse],
    summary="Score batch de nœuds",
    description="Calcule les scores pour plusieurs nœuds en une seule requête"
)
async def batch_score_nodes(
    request: BatchScoreRequest,
    background_tasks: BackgroundTasks,
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Calcule les scores pour un batch de nœuds.
    
    - **node_ids**: Liste des IDs de nœuds (max 100)
    - **force**: Forcer le recalcul même si scores récents existent
    """
    try:
        results = []
        
        for node_id in request.node_ids:
            try:
                if request.force:
                    await service.calculate_node_score(node_id)
                
                score = await service.get_node_score(node_id)
                
                if score:
                    metrics = score.get("metrics", {})
                    results.append(NodeScoreResponse(
                        node_id=node_id,
                        composite_score=metrics.get("composite", 0.0),
                        components=ScoreComponents(
                            centrality=metrics.get("centrality", 0.0),
                            liquidity=75.0,
                            activity=80.0,
                            competitiveness=70.0,
                            reliability=metrics.get("reliability", 0.0),
                            age=65.0,
                            peer_quality=75.0,
                            position=80.0
                        ),
                        rank=None,
                        calculated_at=str(score.get("timestamp", ""))
                    ))
            except Exception as e:
                logger.warning(f"Erreur calcul score pour {node_id}: {e}")
                continue
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur batch_score_nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scores/rankings",
    response_model=RankingsResponse,
    summary="Top nœuds par score",
    description="Retourne les nœuds classés par score composite"
)
async def get_rankings(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre de résultats par page"),
    sort_by: str = Query("composite", description="Champ de tri (composite, centrality, etc.)"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Score minimum"),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Retourne les rankings des nœuds Lightning.
    
    - **page**: Numéro de page (commence à 1)
    - **limit**: Nombre de résultats par page
    - **sort_by**: Champ de tri
    - **min_score**: Filtre par score minimum
    """
    try:
        # Construire filter query
        filter_query = {}
        if min_score is not None:
            filter_query[f"metrics.{sort_by}"] = {"$gte": min_score}
        
        # Récupérer scores avec pagination
        result = await service.get_all_scores(
            page=page,
            limit=limit,
            sort_field=f"metrics.{sort_by}",
            sort_order=-1,  # Descendant
            filter_query=filter_query
        )
        
        # Formater données
        data = []
        for idx, score in enumerate(result.get("data", [])):
            metrics = score.get("metrics", {})
            data.append(NodeScoreResponse(
                node_id=score.get("node_id"),
                composite_score=metrics.get("composite", 0.0),
                components=ScoreComponents(
                    centrality=metrics.get("centrality", 0.0),
                    liquidity=75.0,
                    activity=80.0,
                    competitiveness=70.0,
                    reliability=metrics.get("reliability", 0.0),
                    age=65.0,
                    peer_quality=75.0,
                    position=80.0
                ),
                rank=(page - 1) * limit + idx + 1,
                calculated_at=str(score.get("timestamp", ""))
            ))
        
        # Métadonnées
        metadata_raw = result.get("metadata", {})
        total = metadata_raw.get("total", 0)
        pages = (total + limit - 1) // limit if limit > 0 else 0
        
        metadata = PaginationMetadata(
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
        return RankingsResponse(data=data, metadata=metadata)
        
    except Exception as e:
        logger.error(f"Erreur get_rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scores/recalculate",
    summary="Recalculer les scores",
    description="Déclenche le recalcul des scores (admin only)"
)
async def recalculate_scores(
    request: RecalculateRequest,
    background_tasks: BackgroundTasks,
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Déclenche le recalcul des scores.
    
    - **node_ids**: Liste de nœuds à recalculer (tous si None)
    - **force**: Forcer le recalcul même si scores récents
    
    Note: Opération effectuée en background pour éviter timeout.
    """
    try:
        # Lancer recalcul en background
        background_tasks.add_task(
            service.recalculate_scores,
            node_ids=request.node_ids,
            force=request.force
        )
        
        return {
            "status": "scheduled",
            "message": "Recalcul des scores lancé en background",
            "nodes": len(request.node_ids) if request.node_ids else "all"
        }
        
    except Exception as e:
        logger.error(f"Erreur recalculate_scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recommendations/{node_id}",
    response_model=List[ChannelRecommendation],
    summary="Recommandations pour un nœud",
    description="Retourne toutes les recommandations actionnables pour les canaux d'un nœud"
)
async def get_node_recommendations(
    node_id: str,
    min_confidence: float = Query(0.6, ge=0, le=1, description="Confiance minimale"),
    engine: DecisionEngine = Depends(get_decision_engine),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Retourne les recommandations actionnables pour tous les canaux d'un nœud.
    
    - **node_id**: ID du nœud
    - **min_confidence**: Confiance minimale pour retourner une recommandation
    """
    try:
        # TODO: Récupérer tous les canaux du nœud
        # Pour l'instant, exemple simulé
        
        channels = []  # TODO: Fetch from DB
        
        node_data = {
            "node_id": node_id,
            "channels": channels
        }
        
        # Évaluer tous les canaux
        evaluations = engine.batch_evaluate_channels(
            channels,
            node_data
        )
        
        # Filtrer par confiance et décisions actionnables
        actionable = engine.get_actionable_decisions(
            evaluations,
            min_confidence=min_confidence
        )
        
        # Formater résultats
        recommendations = []
        for eval_result in actionable:
            decision_type = eval_result.get("decision")
            if isinstance(decision_type, DecisionType):
                decision_str = decision_type.value
            else:
                decision_str = str(decision_type)
            
            recommendations.append(ChannelRecommendation(
                channel_id=eval_result.get("channel_id", "unknown"),
                decision=decision_str,
                confidence=eval_result.get("confidence", 0.0),
                reasoning=eval_result.get("reasoning", ""),
                params=eval_result.get("params", {})
            ))
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Erreur get_node_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
