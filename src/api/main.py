from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from src.api.automation_endpoints import router as automation_router
from src.api.rag_endpoints import router as rag_router
from src.api.network_endpoints import router as network_router
# from src.api.notelm_endpoints import router as notelm_router
from src.api.lightning_endpoints import router as lightning_router
from src.api.auth_endpoints import router as auth_router
from src.api.nodes_endpoints import router as nodes_router
from src.api.v2.main import api_v2_router

app = FastAPI(
    title="MCP API",
    description="""
    API pour le système MCP (Monitoring, Control, and Planning) pour Lightning Network.
    
    ## Fonctionnalités principales
    * Système RAG pour l'analyse et la recherche d'informations
      - Évaluation heuristique des documents et requêtes
      - Ajustement dynamique des paramètres de recherche
      - Optimisation de la sélection des documents
    * Analyse du réseau Lightning
    * Automatisation des tâches
    * Gestion des nœuds Lightning
    * Authentification et autorisation
    * API v2 avec fonctionnalités avancées
    
    ## Heuristiques
    Le système utilise des heuristiques pour optimiser les performances :
    * Évaluation de la pertinence des documents
    * Ajustement dynamique des paramètres de recherche
    * Optimisation de la sélection des documents basée sur des scores
    
    ## Authentification
    L'API utilise JWT pour l'authentification. Tous les endpoints (sauf /health) nécessitent un token valide.
    
    ## Rate Limiting
    Les requêtes sont limitées par utilisateur et par endpoint.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer par les origines spécifiques
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion de tous les routers
app.include_router(rag_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")
app.include_router(automation_router, prefix="/api/v1")
# app.include_router(notelm_router, prefix="/api/v1")
app.include_router(lightning_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(nodes_router, prefix="/api/v1")

# Inclusion du router v2
app.include_router(api_v2_router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ajout des informations de sécurité
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Application de la sécurité par défaut
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint racine pour vérifier que l'API est opérationnelle
    """
    return {
        "status": "ok",
        "message": "MCP API is running",
        "version": "2.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
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
            "automation": "ok",
            # "notelm": "ok",
            "lightning": "ok",
            "auth": "ok",
            "nodes": "ok",
            "api_v2": "ok"
        }
    } 