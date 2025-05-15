from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.services.rag_service import get_rag_workflow, check_rag_health
from app.auth import verify_jwt_and_get_tenant

# Création du router
router = APIRouter(prefix="/rag", tags=["rag"])

class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

class IngestRequest(BaseModel):
    documents: List[str]
    metadata: Optional[Dict[str, str]] = None

@router.post("/query")
async def query_rag(request: QueryRequest, rag_workflow = Depends(get_rag_workflow), authorization: str = Header(..., alias="Authorization")):
    """
    Effectue une requête RAG
    """
    tenant_id = verify_jwt_and_get_tenant(authorization)
    try:
        result = await rag_workflow.query(request.query, request.max_results)
        return {
            "status": "success",
            "rapport": result["rapport"],
            "validation_ollama": result["validation_ollama"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_rag_stats(rag_workflow = Depends(get_rag_workflow)):
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

@router.post("/ingest")
async def ingest_documents(request: IngestRequest, rag_workflow = Depends(get_rag_workflow)):
    """
    Ingestion de documents dans le système RAG
    """
    try:
        result = await rag_workflow.ingest_documents_from_list(request.documents, request.metadata)
        return {
            "status": "success",
            "ingested": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_rag_history(rag_workflow = Depends(get_rag_workflow)):
    """
    Récupère l'historique des requêtes RAG
    """
    try:
        history = await rag_workflow.get_query_history()
        return {
            "status": "success",
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def rag_health():
    health = await check_rag_health()
    status = "healthy" if all(health.values()) else "degraded"
    return {"status": status, "details": health} 