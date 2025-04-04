from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from pydantic import BaseModel
from src.rag import RAGWorkflow

# Création du router
router = APIRouter(prefix="/rag", tags=["rag"])

# Initialisation du workflow RAG
rag_workflow = RAGWorkflow()

class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

@router.post("/query")
async def query_rag(request: QueryRequest):
    """
    Effectue une requête RAG
    """
    try:
        results = await rag_workflow.query(request.query, request.max_results)
        return {
            "status": "success",
            "results": results
        }
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