from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional
from pydantic import BaseModel
from src.network_analyzer import NetworkAnalyzer
from src.network_optimizer import NetworkOptimizer
from src.redis_operations import RedisOperations
import os
from app.auth import verify_jwt_and_get_tenant

# Création du router
router = APIRouter(prefix="/network", tags=["network"])

# Configuration Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialisation des composants
redis_ops = RedisOperations(redis_url=REDIS_URL)
network_analyzer = NetworkAnalyzer(redis_ops)
network_optimizer = NetworkOptimizer(redis_ops)

@router.get("/summary")
async def get_network_summary(authorization: str = Header(..., alias="Authorization")):
    """
    Récupère un résumé du réseau Lightning
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        summary = await network_analyzer.get_network_summary()
        return {
            "status": "success",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/centralities")
async def get_network_centralities(authorization: str = Header(..., alias="Authorization")):
    """
    Récupère les centralités du réseau
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        centralities = await network_analyzer.get_network_centralities()
        return {
            "status": "success",
            "centralities": centralities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/stats")
async def get_node_stats(node_id: str, authorization: str = Header(..., alias="Authorization")):
    """
    Récupère les statistiques d'un nœud
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        stats = await network_analyzer.get_node_stats(node_id)
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/node/{node_id}/history")
async def get_node_history(node_id: str, authorization: str = Header(..., alias="Authorization")):
    """
    Récupère l'historique d'un nœud
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        history = await network_analyzer.get_node_history(node_id)
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/node/{node_id}/optimize")
async def optimize_node(node_id: str, authorization: str = Header(..., alias="Authorization")):
    """
    Optimise un nœud
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        result = await network_optimizer.optimize_node(node_id)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 