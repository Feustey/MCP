from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.network_analyzer import NetworkAnalyzer
from src.network_optimizer import NetworkOptimizer
from src.redis_operations import RedisOperations
import os

# Création du router
router = APIRouter(
    prefix="/network",
    tags=["Network"],
    responses={
        401: {"description": "Non authentifié"},
        403: {"description": "Accès refusé"},
        429: {"description": "Trop de requêtes"},
        500: {"description": "Erreur serveur"}
    }
)

# Configuration Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialisation des composants
redis_ops = RedisOperations(redis_url=REDIS_URL)
network_analyzer = NetworkAnalyzer(redis_ops)
network_optimizer = NetworkOptimizer(redis_ops)

class NetworkSummary(BaseModel):
    """
    Modèle pour le résumé du réseau
    """
    total_nodes: int = Field(..., description="Nombre total de nœuds")
    total_channels: int = Field(..., description="Nombre total de canaux")
    total_capacity: float = Field(..., description="Capacité totale du réseau en BTC")
    average_channels_per_node: float = Field(..., description="Nombre moyen de canaux par nœud")
    average_capacity_per_channel: float = Field(..., description="Capacité moyenne par canal en BTC")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_nodes": 15000,
                "total_channels": 75000,
                "total_capacity": 1000.5,
                "average_channels_per_node": 5.0,
                "average_capacity_per_channel": 0.013
            }
        }

class NodeStats(BaseModel):
    """
    Modèle pour les statistiques d'un nœud
    """
    node_id: str = Field(..., description="Identifiant du nœud")
    channels_count: int = Field(..., description="Nombre de canaux")
    total_capacity: float = Field(..., description="Capacité totale en BTC")
    average_capacity: float = Field(..., description="Capacité moyenne par canal en BTC")
    centrality: float = Field(..., description="Score de centralité du nœud")
    
    class Config:
        schema_extra = {
            "example": {
                "node_id": "02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
                "channels_count": 50,
                "total_capacity": 10.5,
                "average_capacity": 0.21,
                "centrality": 0.75
            }
        }

@router.get("/node/{node_id}/stats", response_model=NodeStats)
async def get_node_stats(
    node_id: str = Path(..., description="Identifiant du nœud Lightning")
):
    """
    Récupère les statistiques d'un nœud Lightning.
    
    Cette endpoint fournit des statistiques détaillées sur un nœud Lightning,
    incluant le nombre de canaux, la capacité totale, et les taux de frais.
    """
    try:
        stats = await network_analyzer.get_node_stats(node_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/history")
async def get_node_history(
    node_id: str = Path(..., description="Identifiant du nœud Lightning"),
    limit: int = Query(10, description="Nombre maximum d'entrées à retourner", ge=1, le=100)
):
    """
    Récupère l'historique d'un nœud Lightning.
    
    Cette endpoint fournit l'historique des modifications et événements
    importants pour un nœud Lightning spécifique.
    """
    try:
        history = await network_analyzer.get_node_history(node_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network-summary", response_model=NetworkSummary)
async def get_network_summary():
    """
    Récupère un résumé de l'état du réseau Lightning.
    
    Cette endpoint fournit des statistiques globales sur l'état actuel
    du réseau Lightning, incluant le nombre de nœuds, de canaux et la capacité totale.
    """
    try:
        summary = await network_analyzer.get_network_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/centralities")
async def get_network_centralities(
    metric: str = Query("betweenness", description="Métrique de centralité à calculer", enum=["betweenness", "closeness", "degree"])
):
    """
    Calcule les centralités des nœuds du réseau.
    
    Cette endpoint calcule différentes métriques de centralité pour les nœuds
    du réseau Lightning, permettant d'identifier les nœuds les plus importants.
    """
    try:
        centralities = await network_analyzer.calculate_centralities(metric)
        return centralities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/{node_id}/optimize")
async def optimize_node(
    node_id: str = Path(..., description="Identifiant du nœud Lightning"),
    max_channels: Optional[int] = Query(100, description="Nombre maximum de canaux", ge=1, le=1000),
    min_capacity: Optional[float] = Query(0.1, description="Capacité minimale par canal en BTC", ge=0.01, le=1.0)
):
    """
    Optimise la configuration d'un nœud Lightning.
    
    Cette endpoint analyse et suggère des optimisations pour un nœud Lightning,
    en se basant sur son état actuel et les tendances du réseau.
    """
    try:
        optimization = await network_optimizer.optimize_node(
            node_id,
            max_channels=max_channels,
            min_capacity=min_capacity
        )
        return {
            "status": "success",
            "optimization": optimization
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 