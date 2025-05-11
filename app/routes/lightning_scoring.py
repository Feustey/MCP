# app/routes/lightning_scoring.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from typing import Dict, List, Optional, Any
from motor.core import AgnosticDatabase

from app.db import get_database
from app.models import (
    LightningNodeScore, NodeScoreResponse, ScoresListResponse,
    NodeRecommendations, ScoringConfig, RecalculateScoresRequest
)
from app.services.lightning_scoring import LightningScoreService

# Création du routeur
router = APIRouter(prefix="/api/v1/lightning", tags=["Lightning Scoring"])

# Dépendance pour injecter le service de scoring
async def get_scoring_service(db: AgnosticDatabase = Depends(get_database)) -> LightningScoreService:
    """Fournit une instance du service de scoring pour les routes."""
    return LightningScoreService(db)

@router.get(
    "/scores",
    response_model=ScoresListResponse,
    summary="Liste des scores",
    description="Récupère les scores de tous les nœuds avec pagination, tri et filtrage."
)
async def get_scores(
    service: LightningScoreService = Depends(get_scoring_service),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments par page"),
    sort: str = Query("metrics.composite", description="Champ de tri"),
    order: str = Query("desc", description="Ordre de tri (asc/desc)")
):
    """
    Récupère une liste paginée des scores de nœuds Lightning.
    
    - **page**: Numéro de page (commence à 1)
    - **limit**: Nombre d'éléments par page (max 1000)
    - **sort**: Champ de tri (par défaut metrics.composite)
    - **order**: Ordre de tri (asc/desc)
    """
    # Convertir l'ordre en entier (-1 pour desc, 1 pour asc)
    sort_order = -1 if order.lower() == "desc" else 1
    
    # Récupérer les scores
    return await service.get_all_scores(page, limit, sort, sort_order)

@router.get(
    "/scores/{node_id}",
    response_model=NodeScoreResponse,
    summary="Détails du score d'un nœud",
    description="Récupère les informations détaillées de score pour un nœud spécifique.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Nœud non trouvé"}
    }
)
async def get_node_score(
    node_id: str,
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Récupère les détails du score d'un nœud Lightning.
    
    - **node_id**: Identifiant du nœud (clé publique)
    """
    # Vérifier si le nœud existe
    node_score = await service.get_detailed_node_score(node_id)
    if not node_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud avec ID {node_id} non trouvé ou pas encore évalué."
        )
    
    return node_score

@router.get(
    "/nodes/{node_id}/recommendations",
    response_model=NodeRecommendations,
    summary="Recommandations pour un nœud",
    description="Génère des recommandations pour améliorer le score d'un nœud.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Nœud non trouvé"}
    }
)
async def get_node_recommendations(
    node_id: str,
    type: Optional[str] = Query(None, description="Type de recommandation à filtrer"),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Génère des recommandations pour améliorer le score d'un nœud.
    
    - **node_id**: Identifiant du nœud (clé publique)
    - **type**: Type de recommandation à filtrer (optionnel)
    """
    # Générer les recommandations
    recommendations = await service.generate_recommendations(node_id)
    if not recommendations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nœud avec ID {node_id} non trouvé ou pas encore évalué."
        )
    
    # Filtrer par type si spécifié
    if type:
        recommendations.recommendations = [
            r for r in recommendations.recommendations if r.type == type
        ]
    
    return recommendations

@router.put(
    "/scoring/config",
    response_model=ScoringConfig,
    summary="Configuration du scoring",
    description="Met à jour la configuration du système de scoring."
)
async def update_scoring_config(
    config: ScoringConfig = Body(...),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Met à jour la configuration du système de scoring.
    
    - **config**: Nouvelle configuration
    """
    # Valider que les poids somment à 1
    weights = config.weights
    weights_sum = weights.centrality + weights.reliability + weights.performance
    if abs(weights_sum - 1.0) > 0.001:  # Tolérance pour les erreurs d'arrondi
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La somme des poids doit être égale à 1.0 (actuel: {weights_sum})"
        )
    
    # Mettre à jour la configuration
    updated_config = await service.update_config(config)
    return updated_config

@router.post(
    "/scores/recalculate",
    summary="Recalcul des scores",
    description="Déclenche un recalcul des scores pour les nœuds spécifiés ou tous les nœuds."
)
async def recalculate_scores(
    request: RecalculateScoresRequest = Body(...),
    service: LightningScoreService = Depends(get_scoring_service)
):
    """
    Déclenche un recalcul des scores.
    
    - **node_ids**: Liste des identifiants de nœuds à recalculer (tous si None)
    - **force**: Si True, recalcule même les scores récents
    """
    # Lancer le recalcul
    try:
        count = await service.recalculate_scores(request.node_ids, request.force)
        return {"message": f"{count} scores recalculés avec succès"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du recalcul des scores: {str(e)}"
        ) 