import asyncio
from dotenv import load_dotenv
import aiohttp
import os
from rag import RAGWorkflow
from typing import Optional, Dict, Any, List
from cache_manager import CacheManager
from rate_limiter import RateLimiter
from request_manager import OptimizedRequestManager, PaginatedResponse
from fastapi import FastAPI, Request, Query, Depends, HTTPException, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from retry_manager import retry_manager, RetryConfig
from datetime import datetime

load_dotenv()

def configure_cors(app: FastAPI):
    """Configure CORS for the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialisation du router
router = APIRouter(tags=["lightning"])

rag_workflow = RAGWorkflow()
cache_manager = CacheManager()
rate_limiter = RateLimiter(cache_manager)
request_manager = OptimizedRequestManager(cache_manager, rate_limiter)

def get_headers() -> Dict[str, str]:
    """Get headers with API key for Sparkseer API."""
    api_key = os.getenv('SPARKSEER_API_KEY')
    if not api_key:
        raise ValueError("SPARKSEER_API_KEY not found in environment variables")
    return {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

# Configuration des retries pour différents endpoints
RETRY_CONFIGS = {
    'network_summary': RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    ),
    'centralities': RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    ),
    'node_stats': RetryConfig(
        max_retries=2,
        initial_delay=0.5,
        max_delay=5.0,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    ),
    'node_history': RetryConfig(
        max_retries=2,
        initial_delay=0.5,
        max_delay=5.0,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    )
}

async def make_request(url: str, headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    """Effectue une requête HTTP avec timeout."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            return await response.json()

# Fonctions de fallback
async def fallback_network_summary() -> Dict[str, Any]:
    """Fallback pour le résumé réseau en cas d'échec."""
    return {
        "status": "fallback",
        "message": "Using cached network summary",
        "data": await cache_manager.get("network_summary") or {}
    }

async def fallback_node_stats(node_id: str) -> Dict[str, Any]:
    """Fallback pour les stats de nœud en cas d'échec."""
    return {
        "status": "fallback",
        "message": "Using cached node stats",
        "data": await cache_manager.get(f"node_stats_{node_id}") or {}
    }

@router.post("/optimize-node")
@rate_limiter.rate_limit("optimize")
@retry_manager.with_retry(config=RETRY_CONFIGS['node_stats'], endpoint="optimize_node")
async def optimize_node(
    request: Request,
    node_id: str
):
    """Optimise un nœud Lightning."""
    try:
        # Préparation des requêtes parallèles
        requests = [
            {
                "endpoint": f"/node/{node_id}/stats",
                "params": {},
                "priority": 1
            },
            {
                "endpoint": f"/node/{node_id}/history",
                "params": {},
                "priority": 1
            },
            {
                "endpoint": "/network/centralities",
                "params": {},
                "priority": 2
            }
        ]
        
        # Exécution des requêtes en parallèle
        results = await request_manager.process_batch(requests)
        
        # Analyse des résultats avec OpenAI
        analysis = await rag_workflow.analyze_node_data(results)
        
        return {
            "node_id": node_id,
            "analysis": analysis,
            "recommendations": analysis.get("recommendations", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/network-summary")
async def get_network_summary(request: Request):
    """Récupère un résumé du réseau Lightning."""
    try:
        data = await request_manager.make_request(
            method="GET",
            url="/network-summary"
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/centralities")
@rate_limiter.rate_limit("network")
@retry_manager.with_retry(config=RETRY_CONFIGS['centralities'], endpoint="centralities")
async def get_centralities(
    request: Request
):
    """Récupère les centralités des nœuds."""
    try:
        return await request_manager.make_request(
            method="GET",
            url="https://api.sparkseer.com/network/centralities",
            timeout=10
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/node/{node_id}/stats")
@rate_limiter.rate_limit("node")
@retry_manager.with_retry(config=RETRY_CONFIGS['node_stats'], endpoint="node_stats")
@retry_manager.with_fallback(fallback_node_stats, endpoint="node_stats")
async def get_node_stats(
    request: Request,
    node_id: str
):
    """Récupère les statistiques d'un nœud."""
    try:
        return await request_manager.make_request(
            method="GET",
            url=f"https://api.sparkseer.com/node/{node_id}/stats",
            timeout=5
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/node/{node_id}/history")
@rate_limiter.rate_limit("node")
@retry_manager.with_retry(config=RETRY_CONFIGS['node_history'], endpoint="node_history")
async def get_node_history(
    request: Request,
    node_id: str
):
    """Récupère l'historique d'un nœud."""
    try:
        return await request_manager.make_request(
            method="GET",
            url=f"https://api.sparkseer.com/node/{node_id}/history",
            timeout=5
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/node/{node_id}/optimize")
@rate_limiter.rate_limit("optimize")
@retry_manager.with_retry(config=RETRY_CONFIGS['node_stats'], endpoint="optimize_node")
async def optimize_node_complete(
    request: Request,
    node_id: str
):
    """Endpoint complet pour l'optimisation d'un nœud Lightning."""
    try:
        # 1. Récupération des données brutes de Sparkseer
        node_data = {
            "stats": await request_manager.make_request(
                method="GET",
                url=f"https://api.sparkseer.com/node/{node_id}/stats",
                timeout=5
            ),
            "history": await request_manager.make_request(
                method="GET",
                url=f"https://api.sparkseer.com/node/{node_id}/history",
                timeout=5
            ),
            "network_context": await request_manager.make_request(
                method="GET",
                url="https://api.sparkseer.com/network/centralities",
                timeout=10
            )
        }

        # 2. Analyse des données via RAG
        rag_analysis = await rag_workflow.analyze_node_data(node_data)

        # 3. Génération des recommandations via OpenAI
        recommendations = await rag_workflow._generate_recommendations(node_data)

        return {
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "raw_data": node_data,
            "rag_analysis": rag_analysis,
            "recommendations": recommendations,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/health")
async def health_check():
    """Vérifie l'état de l'API et retourne les statistiques de retry/fallback."""
    try:
        # Vérification de l'état de l'API Sparkseer
        sparkseer_status = "healthy"
        try:
            # Crée une requête factice pour le health check
            mock_request = Request(scope={"type": "http", "method": "GET", "path": "/health"})
            await get_network_summary(mock_request)
        except Exception as e:
            sparkseer_status = f"unhealthy: {str(e)}"

        # Récupération des statistiques de retry et fallback
        retry_stats = {
            endpoint: retry_manager.get_retry_stats(endpoint)
            for endpoint in ["network_summary", "centralities", "node_stats", "node_history", "optimize_node"]
        }
        
        fallback_stats = {
            endpoint: retry_manager.get_fallback_stats(endpoint)
            for endpoint in ["network_summary", "node_stats"]
        }

        return {
            "status": "healthy",
            "sparkseer_status": sparkseer_status,
            "retry_stats": retry_stats,
            "fallback_stats": fallback_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def cleanup():
    """Cleanup function to close Redis connection."""
    await cache_manager.close()

if __name__ == "__main__":
    asyncio.run(rag_workflow.ingest_documents("data"))
    mcp.run(transport="stdio")
