"""
Routes RAG pour l'API MCP
Endpoints pour le système de Retrieval-Augmented Generation
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.services.rag_service import get_rag_workflow, check_rag_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

# Modèles Pydantic pour les requêtes/réponses
class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Question ou requête à traiter")
    n_results: int = Field(default=5, ge=1, le=20, description="Nombre de résultats à retourner")
    temperature: float = Field(default=0.7, ge=0, le=1, description="Température pour la génération")
    max_tokens: Optional[int] = Field(default=500, description="Nombre max de tokens pour la réponse")
    use_cache: bool = Field(default=True, description="Utiliser le cache si disponible")

class RAGIndexRequest(BaseModel):
    content: str = Field(..., description="Contenu à indexer")
    source: str = Field(..., description="Source du document")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Métadonnées additionnelles")

class RAGResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    processing_time_ms: float
    cached: bool = False

@router.get("/health",
    summary="Santé du Système RAG",
    description="Vérifie l'état opérationnel du système RAG et ses dépendances",
    responses={
        200: {
            "description": "Système RAG opérationnel",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "components": {
                            "redis": True,
                            "mongo": True,
                            "rag_instance": True
                        },
                        "timestamp": "2025-01-09T12:00:00.000000"
                    }
                }
            }
        },
        500: {"description": "Erreur système RAG"}
    }
)
async def rag_health():
    """
    **Vérification de Santé du Système RAG**

    Vérifie l'état opérationnel de tous les composants RAG:
    - Redis (cache)
    - MongoDB (stockage vectoriel)
    - Instance RAG (workflow)

    Retourne `healthy` si tous les composants sont opérationnels.
    """
    try:
        health_status = await check_rag_health()
        
        is_healthy = all([
            health_status.get("redis", False),
            health_status.get("mongo", False),
            health_status.get("rag_instance", False)
        ])
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "components": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur health check RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query",
    response_model=RAGResponse,
    summary="Requête RAG",
    description="Effectue une requête de recherche et génération augmentée",
    responses={
        200: {
            "description": "Réponse générée avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "answer": "Voici la réponse basée sur les documents indexés...",
                        "sources": [
                            {"source": "doc1.md", "score": 0.95, "content": "..."},
                            {"source": "doc2.md", "score": 0.87, "content": "..."}
                        ],
                        "confidence_score": 0.92,
                        "processing_time_ms": 234.5,
                        "cached": False
                    }
                }
            }
        },
        500: {"description": "Erreur lors du traitement de la requête"}
    }
)
async def query_rag(request: RAGQueryRequest):
    """
    **Requête RAG - Recherche et Génération Augmentée**

    Effectue une recherche sémantique dans les documents indexés
    et génère une réponse contextuelle basée sur les sources trouvées.

    **Paramètres:**
    - `query`: Question ou requête textuelle
    - `n_results`: Nombre de sources à considérer (1-20)
    - `temperature`: Créativité de la réponse (0-1)
    - `max_tokens`: Longueur maximale de la réponse
    - `use_cache`: Utiliser le cache pour réponses similaires

    **Retourne:**
    - `answer`: Réponse générée
    - `sources`: Documents sources utilisés
    - `confidence_score`: Score de confiance (0-1)
    - `processing_time_ms`: Temps de traitement
    - `cached`: Indique si réponse vient du cache
    """
    try:
        start_time = datetime.utcnow()
        
        # Obtenir l'instance RAG
        rag = await get_rag_workflow()
        
        # Effectuer la requête
        result = await rag.process_query(
            query=request.query,
            n_results=request.n_results,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_cache=request.use_cache
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return RAGResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            confidence_score=result.get("confidence_score", 0.0),
            processing_time_ms=processing_time,
            cached=result.get("cached", False)
        )
        
    except Exception as e:
        logger.error(f"Erreur requête RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index")
async def index_content(request: RAGIndexRequest):
    """
    Indexer du nouveau contenu dans le système RAG
    
    Args:
        request: Contenu à indexer avec métadonnées
    
    Returns:
        Statut de l'indexation
    """
    try:
        # Obtenir l'instance RAG
        rag = await get_rag_workflow()
        
        # Indexer le contenu
        result = await rag.index_content(
            content=request.content,
            source=request.source,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "indexed": True,
            "document_id": result.get("document_id"),
            "chunks_created": result.get("chunks_created", 0),
            "metadata": result.get("metadata", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur indexation RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index-file")
async def index_file(
    file: UploadFile = File(...),
    source: str = "uploaded_file"
):
    """
    Indexer un fichier dans le système RAG
    
    Args:
        file: Fichier à indexer
        source: Source du fichier
    
    Returns:
        Statut de l'indexation
    """
    try:
        # Vérifier le type de fichier
        allowed_extensions = [".txt", ".md", ".json", ".pdf", ".html"]
        file_extension = "." + file.filename.split(".")[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Extensions autorisées: {allowed_extensions}"
            )
        
        # Lire le contenu
        content = await file.read()
        content_str = content.decode("utf-8")
        
        # Obtenir l'instance RAG
        rag = await get_rag_workflow()
        
        # Indexer le contenu
        result = await rag.index_content(
            content=content_str,
            source=f"{source}/{file.filename}",
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(content)
            }
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content),
            "document_id": result.get("document_id"),
            "chunks_created": result.get("chunks_created", 0),
            "metadata": result.get("metadata", []),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Impossible de décoder le fichier")
    except Exception as e:
        logger.error(f"Erreur indexation fichier: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear-cache")
async def clear_cache():
    """Vider le cache du système RAG"""
    try:
        rag = await get_rag_workflow()
        result = await rag.clear_cache()

        return {
            "status": "success",
            "message": "Cache vidé avec succès",
            "details": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur suppression cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats():
    """Obtenir les statistiques du système RAG"""
    try:
        rag = await get_rag_workflow()
        stats = await rag.get_stats()

        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur récupération stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reindex")
async def reindex_all():
    """Réindexer tout le contenu (opération longue)"""
    try:
        rag = await get_rag_workflow()
        result = await rag.reindex_all()
        
        return {
            "status": "success",
            "documents_processed": result.get("documents_processed", 0),
            "chunks_created": result.get("chunks_created", 0),
            "errors": result.get("errors", []),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erreur réindexation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
