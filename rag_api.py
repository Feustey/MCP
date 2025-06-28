#!/usr/bin/env python3
"""
API RAG simple pour MCP avec Ollama
Dernière mise à jour: 25 mai 2025
"""

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, Field
import httpx
import asyncio
import uvicorn
from datetime import datetime
import logging
from typing import List, Optional, Dict, Any

from config.rag_config import settings
from rag.ollama_client import OllamaClient
from rag.cache import cache
from rag.metrics import track_metrics

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Modèles Pydantic
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    model: str = Field(default=settings.OLLAMA_DEFAULT_MODEL)
    max_length: int = Field(default=500, ge=1, le=2000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)

class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    model: str = Field(default=settings.OLLAMA_DEFAULT_MODEL)

class AnalysisRequest(BaseModel):
    node_data: Dict[str, Any]
    analysis_type: str = Field(default="fee_optimization")

# Configuration de l'API
app = FastAPI(
    title=settings.API_TITLE,
    description="API pour le système RAG Lightning Network avec Ollama",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de l'authentification
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER)

async def get_api_key(api_key: str = Security(api_key_header)):
    """Vérifie la clé API."""
    # TODO: Implémenter la vérification de la clé API
    return api_key

# Instance globale du client Ollama
ollama_client = OllamaClient()

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage."""
    # Initialiser le rate limiter
    await FastAPILimiter.init(cache.redis)

@app.get("/")
async def root():
    """Page d'accueil de l'API RAG."""
    return {
        "service": settings.API_TITLE,
        "status": "running",
        "version": settings.API_VERSION,
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/health",
            "/models",
            "/query",
            "/embed",
            "/analyze",
            "/lightning/optimize",
            "/docs"
        ]
    }

@app.get("/health")
@track_metrics(metric_type='query')
async def health_check():
    """Vérification de santé incluant Ollama."""
    ollama_status = await ollama_client.test_connection()
    
    return {
        "status": "healthy" if ollama_status else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "ollama": "connected" if ollama_status else "disconnected"
        },
        "ollama_url": ollama_client.base_url
    }

@app.get("/models")
@track_metrics(metric_type='query')
async def get_available_models():
    """Récupère les modèles disponibles dans Ollama."""
    models = await ollama_client.get_models()
    return {
        "available_models": models.get("models", []),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/query")
@track_metrics(metric_type='query')
@RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, minutes=1)
async def rag_query(
    request: QueryRequest,
    api_key: str = Depends(get_api_key)
):
    """Effectue une requête RAG avec contexte Lightning Network."""
    
    # Construire le prompt avec contexte Lightning Network
    lightning_context = """
Tu es un expert en Lightning Network et en optimisation de nœuds. Tu dois répondre aux questions 
avec une expertise technique approfondie sur:
- Configuration des frais (base fee, fee rate)
- Gestion de la liquidité (inbound/outbound)
- Routing et pathfinding
- Monitoring et métriques
- Stratégies d'optimisation des revenus
- Sécurité et best practices

Contexte Lightning Network:
- Les nœuds génèrent des revenus en routant des paiements
- Les frais doivent être équilibrés (ni trop hauts, ni trop bas)
- La liquidité doit être bien répartie pour maximiser les opportunités de routing
- Le monitoring est crucial pour détecter les problèmes rapidement
"""
    
    full_prompt = f"{lightning_context}\n\nQuestion: {request.query}\n\nRéponse:"
    
    try:
        response = await ollama_client.generate_response(
            prompt=full_prompt,
            model=request.model,
            max_tokens=request.max_length,
            temperature=request.temperature
        )
        
        return {
            "query": request.query,
            "response": response,
            "model": request.model,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la requête RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed")
@track_metrics(metric_type='embedding')
@RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, minutes=1)
async def generate_embedding(
    request: EmbeddingRequest,
    api_key: str = Depends(get_api_key)
):
    """Génère un embedding pour un texte."""
    try:
        embedding = await ollama_client.get_embedding(
            text=request.text,
            model=request.model
        )
        
        return {
            "text": request.text,
            "embedding": embedding,
            "dimension": len(embedding),
            "model": request.model,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de la génération d'embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
@track_metrics(metric_type='query')
@RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, minutes=1)
async def analyze_data(
    request: AnalysisRequest,
    api_key: str = Depends(get_api_key)
):
    """Analyse des données Lightning Network."""
    
    node_data = request.node_data
    analysis_type = request.analysis_type
    
    # Construire le prompt d'analyse
    if analysis_type == "fee_optimization":
        prompt = f"""
Analyse les données suivantes d'un nœud Lightning Network et fournis des recommandations d'optimisation des frais:

Données du nœud:
{node_data}

Fournis une analyse structurée avec:
1. État actuel du nœud
2. Points d'amélioration identifiés  
3. Recommandations concrètes pour les frais
4. Stratégies de liquidité
5. Actions prioritaires

Sois précis et actionnable dans tes recommandations.
"""
    else:
        prompt = f"""
Analyse générale des données Lightning Network:

Données:
{node_data}

Fournis une analyse complète avec insights et recommandations.
"""
    
    try:
        analysis = await ollama_client.generate_response(prompt)
        
        return {
            "node_data": node_data,
            "analysis_type": analysis_type,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/lightning/optimize")
async def optimize_lightning_node(node_data: dict):
    """Optimisation spécifique pour nœuds Lightning."""
    
    prompt = f"""
En tant qu'expert Lightning Network, analyse ce nœud et fournis des recommandations d'optimisation:

DONNÉES DU NŒUD:
{node_data}

ANALYSE DEMANDÉE:
1. Configuration des frais actuelle
2. État de la liquidité
3. Performance de routing
4. Recommandations d'amélioration
5. Actions immédiates à prendre

Fournis des recommandations CONCRÈTES et ACTIONNABLES avec des valeurs numériques précises.
"""
    
    optimization = await ollama_client.generate_response(prompt)
    
    return {
        "node_data": node_data,
        "optimization_recommendations": optimization,
        "timestamp": datetime.now().isoformat(),
        "expert_system": "MCP RAG Lightning Optimizer"
    }

@app.get("/lightning/health/{node_id}")
async def node_health_check(node_id: str):
    """Vérification de santé d'un nœud Lightning."""
    
    # Simuler une vérification de santé
    prompt = f"""
Effectue une vérification de santé pour le nœud Lightning {node_id}.

Vérifie:
1. Connectivité réseau
2. État des channels
3. Liquidité disponible
4. Performance récente
5. Alertes potentielles

Fournis un rapport de santé structuré.
"""
    
    health_report = await ollama_client.generate_response(prompt)
    
    return {
        "node_id": node_id,
        "health_status": "checked",
        "report": health_report,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 