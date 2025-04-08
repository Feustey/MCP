import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from .rag import RAGWorkflow
from .prisma_operations import PrismaOperations
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
prisma_ops = PrismaOperations()

# Gestionnaires d'événements pour la connexion Prisma
@app.on_event("startup")
async def startup_event():
    logger.info("Connexion à Prisma...")
    await prisma_ops.connect()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Déconnexion de Prisma...")
    await prisma_ops.disconnect()

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
        # Utilisation de prisma_ops
        stats = await prisma_ops.get_system_stats()
        # Les objets retournés par Prisma Client Py sont déjà des dictionnaires ou des objets similaires
        # Pas besoin de .model_dump() comme avec Pydantic, sauf si on veut forcer une structure spécifique
        # Convertir l'objet Prisma (s'il existe) en un dictionnaire standard pour la sérialisation JSON
        # Accéder aux attributs directement peut être plus sûr que .__dict__
        if stats:
            return {
                "id": stats.id,
                "total_documents": stats.total_documents,
                "total_queries": stats.total_queries,
                "average_processing_time": stats.average_processing_time,
                "cache_hit_rate": stats.cache_hit_rate,
                "last_update": stats.last_update.isoformat() if stats.last_update else None
            }
        else:
            return {}
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recent-queries")
async def get_recent_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """Endpoint pour l'historique des requêtes récentes."""
    try:
        # Utilisation de prisma_ops
        queries = await prisma_ops.get_recent_queries(limit)
        # Convertir les objets Prisma en dictionnaires simples pour la réponse JSON
        # Accéder aux attributs directement
        results = []
        for query in queries:
            results.append({
                "id": query.id,
                "query": query.query,
                "response": query.response,
                "context_docs": query.context_docs,
                "processing_time": query.processing_time,
                "cache_hit": query.cache_hit,
                "metadata": query.metadata, # Déjà désérialisé par prisma_ops
                "timestamp": query.timestamp.isoformat() if query.timestamp else None
            })
        return results
    except Exception as e:
        logger.error(f"Error getting recent queries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 