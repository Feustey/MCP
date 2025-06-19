"""
API simplifiée pour le système MCP (Moniteur et Contrôleur de Performance)

Version simplifiée sans base de données pour le déploiement Hostinger.
Dernière mise à jour: 9 mai 2025
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
from pathlib import Path

# Import de la configuration simplifiée
from .config_simple import settings

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-api-simple")

# Initialisation de l'application FastAPI
app = FastAPI(
    title="MCP - Moniteur et Contrôleur de Performance (Simplifié)",
    description="API simplifiée pour l'optimisation et la simulation de nœuds Lightning Network",
    version=settings.version
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware pour le logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour enregistrer les requêtes entrantes"""
    start_time = datetime.now()
    response = await call_next(request)
    process_time = datetime.now() - start_time
    logger.info(f"[{request.method}] {request.url.path} - {response.status_code} - {process_time.total_seconds():.3f}s")
    return response

# Route de santé
@app.get("/health")
async def health_check():
    """Vérifie l'état de santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "dry_run": settings.dry_run,
        "mode": "simplified"
    }

# Route racine
@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "MCP - Moniteur et Contrôleur de Performance (Simplifié)",
        "version": settings.version,
        "environment": settings.environment,
        "documentation": "/docs",
        "health": "/health",
        "features": {
            "simulation": False,
            "optimization": False,
            "database": False,
            "redis": False
        }
    }

# Endpoint pour la configuration
@app.get("/api/v1/config")
async def get_config():
    """Récupère la configuration actuelle de l'application"""
    return {
        "environment": settings.environment,
        "dry_run": settings.dry_run,
        "version": settings.version,
        "mode": "simplified",
        "features": {
            "simulation": False,
            "optimization": False,
            "database": False,
            "redis": False
        }
    }

# Endpoint pour les métriques du tableau de bord
@app.get("/api/v1/dashboard/metrics")
async def get_dashboard_metrics():
    """Récupère les métriques pour le tableau de bord"""
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "status": "operational",
            "version": settings.version,
            "environment": settings.environment,
            "dry_run": settings.dry_run,
            "mode": "simplified"
        },
        "api": {
            "endpoints_available": len(app.routes),
            "health_status": "healthy"
        },
        "features": {
            "simulation": False,
            "optimization": False,
            "database": False,
            "redis": False
        }
    }

# Endpoint pour tester les fonctionnalités
@app.get("/api/v1/test")
async def test_endpoint():
    """Endpoint de test pour vérifier le fonctionnement"""
    return {
        "message": "API MCP simplifiée fonctionnelle",
        "timestamp": datetime.now().isoformat(),
        "environment": settings.environment,
        "dry_run": settings.dry_run
    }

# Endpoint pour les informations système
@app.get("/api/v1/system/info")
async def system_info():
    """Informations système"""
    import platform
    import psutil
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available
        },
        "application": {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "dry_run": settings.dry_run
        }
    }

# Gestionnaire d'erreurs global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs global"""
    logger.error(f"Erreur non gérée: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        log_level=settings.log_level.lower()
    ) 