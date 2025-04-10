from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.rag import RAGWorkflow
from src.redis_operations import RedisOperations
import os

# Création du router
router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
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
rag_workflow = RAGWorkflow(redis_ops)

class QueryRequest(BaseModel):
    """
    Modèle de requête pour le système RAG
    """
    query: str = Field(..., description="La question ou requête à traiter")
    max_results: Optional[int] = Field(
        default=5,
        description="Nombre maximum de résultats à retourner",
        ge=1,
        le=20
    )
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Quelle est la meilleure façon d'optimiser un nœud Lightning ?",
                "max_results": 5
            }
        }

class QueryResponse(BaseModel):
    """
    Modèle de réponse du système RAG
    """
    response: str = Field(..., description="La réponse générée")
    sources: List[str] = Field(default_factory=list, description="Liste des sources utilisées")
    processing_time: float = Field(..., description="Temps de traitement en secondes")
    cache_hit: bool = Field(..., description="Indique si la réponse vient du cache")

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    cache_ttl: Optional[int] = Query(
        default=3600,
        description="Durée de vie du cache en secondes",
        ge=0,
        le=86400
    )
):
    """
    Soumet une requête au système RAG.
    
    Cette endpoint permet d'interroger le système RAG avec une question spécifique.
    La réponse est générée en utilisant le contexte disponible et peut être mise en cache.
    
    - **query**: La question à traiter
    - **max_results**: Nombre maximum de résultats à retourner (1-20)
    - **cache_ttl**: Durée de vie du cache en secondes (0-86400)
    
    Returns:
        QueryResponse: La réponse générée avec les métadonnées associées
    """
    try:
        response = await rag_workflow.query(
            request.query,
            max_results=request.max_results,
            cache_ttl=cache_ttl
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest_documents(
    directory: str = Query(..., description="Chemin du répertoire contenant les documents à ingérer"),
    recursive: bool = Query(
        default=True,
        description="Si True, ingère récursivement les sous-répertoires"
    )
):
    """
    Ingère des documents depuis un répertoire spécifié.
    
    Cette endpoint permet d'ajouter de nouveaux documents au système RAG.
    Les documents sont traités et indexés pour être utilisés dans les requêtes futures.
    
    - **directory**: Chemin du répertoire contenant les documents
    - **recursive**: Si True, traite également les sous-répertoires
    
    Returns:
        dict: Statut de l'opération
    """
    try:
        success = await rag_workflow.ingest_documents(directory, recursive=recursive)
        return {"status": "success" if success else "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats():
    """
    Récupère les statistiques du système RAG
    """
    try:
        stats = await rag_workflow.get_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 