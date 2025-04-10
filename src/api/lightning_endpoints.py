from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.lightning_validator import LightningValidator
from src.lightning_optimizer import LightningOptimizer
from src.redis_operations import RedisOperations
import os

# Création du router
router = APIRouter(
    prefix="/lightning",
    tags=["Lightning"],
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
lightning_validator = LightningValidator(redis_ops)
lightning_optimizer = LightningOptimizer(redis_ops)

class ValidationResponse(BaseModel):
    """
    Modèle de réponse pour la validation
    """
    is_valid: bool = Field(..., description="Indique si la validation est réussie")
    message: str = Field(..., description="Message détaillant le résultat de la validation")
    details: Optional[Dict] = Field(None, description="Détails supplémentaires sur la validation")

class NodeStats(BaseModel):
    """
    Modèle pour les statistiques d'un nœud
    """
    node_id: str = Field(..., description="Identifiant du nœud")
    total_channels: int = Field(..., description="Nombre total de canaux")
    total_capacity: float = Field(..., description="Capacité totale en BTC")
    average_fee_rate: float = Field(..., description="Taux de frais moyen en ppm")
    uptime: float = Field(..., description="Temps de fonctionnement en heures")
    last_updated: str = Field(..., description="Date de dernière mise à jour")

class NetworkSummary(BaseModel):
    """
    Modèle pour le résumé du réseau
    """
    total_nodes: int = Field(..., description="Nombre total de nœuds")
    total_channels: int = Field(..., description="Nombre total de canaux")
    total_capacity: float = Field(..., description="Capacité totale du réseau en BTC")
    average_channels_per_node: float = Field(..., description="Nombre moyen de canaux par nœud")
    average_capacity_per_channel: float = Field(..., description="Capacité moyenne par canal en BTC")

@router.post("/validate-key", response_model=ValidationResponse)
async def validate_lightning_key(pubkey: str = Query(..., description="Clé publique Lightning à valider")):
    """
    Valide une clé publique Lightning.
    
    Cette endpoint vérifie si une clé publique Lightning est valide
    et retourne des informations détaillées sur la validation.
    """
    try:
        result = await lightning_validator.validate_pubkey(pubkey)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-node", response_model=ValidationResponse)
async def validate_lightning_node(node_id: str = Query(..., description="ID du nœud Lightning à valider")):
    """
    Valide un nœud Lightning.
    
    Cette endpoint vérifie si un nœud Lightning est valide et actif
    sur le réseau, et retourne des informations détaillées sur la validation.
    """
    try:
        result = await lightning_validator.validate_node(node_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/stats", response_model=NodeStats)
async def get_node_stats(node_id: str):
    """
    Récupère les statistiques d'un nœud Lightning.
    
    Cette endpoint fournit des statistiques détaillées sur un nœud Lightning,
    incluant le nombre de canaux, la capacité totale, et les taux de frais.
    """
    try:
        stats = await lightning_optimizer.get_node_stats(node_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/history")
async def get_node_history(
    node_id: str,
    limit: int = Query(10, description="Nombre maximum d'entrées à retourner", ge=1, le=100)
):
    """
    Récupère l'historique d'un nœud Lightning.
    
    Cette endpoint fournit l'historique des modifications et événements
    importants pour un nœud Lightning spécifique.
    """
    try:
        history = await lightning_optimizer.get_node_history(node_id, limit)
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
        summary = await lightning_optimizer.get_network_summary()
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
        centralities = await lightning_optimizer.calculate_centralities(metric)
        return centralities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/{node_id}/optimize")
async def optimize_node(
    node_id: str,
    max_channels: Optional[int] = Query(100, description="Nombre maximum de canaux", ge=1, le=1000),
    min_capacity: Optional[float] = Query(0.1, description="Capacité minimale par canal en BTC", ge=0.01, le=1.0)
):
    """
    Optimise la configuration d'un nœud Lightning.
    
    Cette endpoint analyse et suggère des optimisations pour un nœud Lightning,
    en se basant sur son état actuel et les tendances du réseau.
    """
    try:
        optimization = await lightning_optimizer.optimize_node(
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