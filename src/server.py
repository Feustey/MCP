import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from .rag import RAGWorkflow
from .mongo_operations import MongoOperations
from typing import Dict, Any, List
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des composants
rag_workflow = RAGWorkflow()
mongo_ops = MongoOperations()

def get_headers() -> Dict[str, str]:
    """Retourne les en-têtes pour les requêtes API."""
    return {
        "api-key": os.getenv("SPARKSEER_API_KEY", ""),
        "Content-Type": "application/json"
    }

async def get_network_summary() -> Dict[str, Any]:
    """Récupère le résumé du réseau."""
    try:
        # Implémentation à venir
        return {"status": "success", "message": "Network summary endpoint"}
    except Exception as e:
        logger.error(f"Error getting network summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_centralities() -> Dict[str, Any]:
    """Récupère les centralités du réseau."""
    try:
        # Implémentation à venir
        return {"status": "success", "message": "Centralities endpoint"}
    except Exception as e:
        logger.error(f"Error getting centralities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def read_root():
    """Endpoint racine."""
    return {"message": "Welcome to the RAG API"}

@app.post("/query")
async def query(query_text: str) -> Dict[str, Any]:
    """Endpoint pour les requêtes RAG."""
    try:
        response = await rag_workflow.query(query_text)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_documents(directory: str) -> Dict[str, Any]:
    """Endpoint pour l'ingestion de documents."""
    try:
        success = await rag_workflow.ingest_documents(directory)
        return {"status": "success" if success else "error"}
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Endpoint pour les statistiques du système."""
    try:
        stats = await mongo_ops.get_system_stats()
        return stats.model_dump() if stats else {}
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent-queries")
async def get_recent_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """Endpoint pour l'historique des requêtes récentes."""
    try:
        queries = await mongo_ops.get_recent_queries(limit)
        return [query.model_dump() for query in queries]
    except Exception as e:
        logger.error(f"Error getting recent queries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 