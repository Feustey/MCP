from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from src.lnplus_integration import (
    LNPlusClient,
    SwapService,
    NodeMetricsService,
    RatingService,
    RecommendationService,
    LightningSwap,
    SwapCreationRequest,
    NodeMetrics,
    Rating
)
from src.auth import get_current_user

router = APIRouter(prefix="/v2/lnplus")

# Initialisation des services
lnplus_client = LNPlusClient(api_key="YOUR_API_KEY")
swap_service = SwapService(lnplus_client)
node_metrics_service = NodeMetricsService(lnplus_client)
rating_service = RatingService(lnplus_client)
recommendation_service = RecommendationService(lnplus_client)

@router.get("/swaps/available", response_model=List[LightningSwap])
async def get_available_swaps(
    min_capacity: Optional[int] = None,
    max_participants: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    """Liste les swaps disponibles"""
    try:
        return await swap_service.get_available_swaps(min_capacity, max_participants)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/swaps/create", response_model=LightningSwap)
async def create_swap(
    swap_request: SwapCreationRequest,
    current_user = Depends(get_current_user)
):
    """Crée un nouveau swap"""
    try:
        return await swap_service.create_swap(swap_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_id}/metrics", response_model=NodeMetrics)
async def get_node_metrics(
    node_id: str,
    current_user = Depends(get_current_user)
):
    """Récupère les métriques d'un nœud"""
    try:
        return await node_metrics_service.get_enhanced_metrics(node_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ratings", response_model=Rating)
async def create_rating(
    target_node_id: str,
    is_positive: bool,
    comment: str,
    current_user = Depends(get_current_user)
):
    """Crée une notation pour un nœud"""
    try:
        return await rating_service.create_rating(
            target_node_id,
            is_positive,
            comment,
            current_user.node_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nodes/{node_id}/recommendations")
async def get_node_recommendations(
    node_id: str,
    min_capacity: int = 100000,
    current_user = Depends(get_current_user)
):
    """Récupère les recommandations pour un nœud"""
    try:
        return await recommendation_service.get_enhanced_recommendations(
            node_id,
            min_capacity
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 