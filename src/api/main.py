from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.automation_endpoints import router as automation_router
from src.api.rag_endpoints import router as rag_router
from src.api.network_endpoints import router as network_router

app = FastAPI(
    title="MCP API",
    description="API pour le système MCP (Monitoring, Control, and Planning) pour Lightning Network",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer par les origines spécifiques
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(rag_router)
app.include_router(network_router)
app.include_router(automation_router)

@app.get("/")
async def root():
    """
    Endpoint racine pour vérifier que l'API est opérationnelle
    """
    return {
        "status": "ok",
        "message": "MCP API is running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """
    Endpoint de vérification de santé
    """
    return {
        "status": "healthy",
        "services": {
            "rag": "ok",
            "network": "ok",
            "automation": "ok"
        }
    } 