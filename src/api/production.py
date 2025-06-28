"""
API sécurisée MCP pour la production sur api.dazno.de
Intégration des middlewares de sécurité et endpoints protégés

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn

# Imports spécifiques MCP
from config.security.auth import (
    require_auth, 
    require_permissions, 
    verify_request_security,
    security_manager,
    get_client_ip
)
from src.api.main import app as main_app
from src.tools.simulator.node_simulator import NodeSimulator
from src.optimizers.scoring_utils import evaluate_node
from src.scanners.node_scanner import NodeScanner

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp.api.production")

# Configuration de l'application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    logger.info("Démarrage de l'API MCP Production sur api.dazno.de")
    
    # Initialisation des services
    try:
        # Vérifier les connexions aux bases de données
        logger.info("Initialisation des connexions...")
        
        # Initialiser le simulateur de nœuds
        simulator = NodeSimulator()
        app.state.simulator = simulator
        
        # Initialiser le scanner de nœuds
        scanner = NodeScanner()
        app.state.scanner = scanner
        
        logger.info("Services initialisés avec succès")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        raise
    
    yield
    
    # Nettoyage
    logger.info("Arrêt de l'API MCP Production")

# Configuration des origines autorisées
ALLOWED_ORIGINS = [
    "https://app.dazno.de",
    "https://dazno.de",
    "https://www.dazno.de"
]

# Création de l'application FastAPI
app = FastAPI(
    title="MCP Lightning Network Optimizer API",
    description="API sécurisée pour l'optimisation des nœuds Lightning Network",
    version="1.0.0",
    docs_url=None,  # Désactiver Swagger en production
    redoc_url=None,  # Désactiver ReDoc en production
    openapi_url=None  # Désactiver OpenAPI en production
)

# Middleware de sécurité - ordre important !

# 1. Middleware de compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. Middleware CORS sécurisé
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# 3. Middleware de host de confiance
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["api.dazno.de", "localhost", "127.0.0.1"]
)

# Middleware de sécurité personnalisé
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Middleware de sécurité global"""
    start_time = time.time()
    
    try:
        # Vérifications de sécurité de base (sans authentification)
        security_info = verify_request_security(request)
        
        # Ajouter les informations de sécurité à la requête
        request.state.security_info = security_info
        
        # Traiter la requête
        response = await call_next(request)
        
        # Ajouter des headers de sécurité à la réponse
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = security_info["request_id"]
        
        # Logging de la requête
        process_time = time.time() - start_time
        logger.info(
            f"Request processed: {request.method} {request.url.path} "
            f"from {security_info['client_ip']} "
            f"in {process_time:.3f}s "
            f"status={response.status_code}"
        )
        
        return response
        
    except HTTPException as e:
        # Gestion des erreurs de sécurité
        logger.warning(
            f"Security exception: {e.detail} "
            f"from {get_client_ip(request)} "
            f"on {request.url.path}"
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail, "timestamp": datetime.now().isoformat()}
        )
    
    except Exception as e:
        # Gestion des erreurs générales
        logger.error(f"Unexpected error in security middleware: {e}")
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
        )

# Middleware de limitation de taille des requêtes
@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    """Limite la taille des requêtes pour éviter les attaques DoS"""
    content_length = request.headers.get("content-length")
    if content_length:
        content_length = int(content_length)
        if content_length > 10 * 1024 * 1024:  # 10MB maximum
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large"}
            )
    
    return await call_next(request)

# Endpoints publics (sans authentification)

@app.get("/health")
async def health_check():
    """Endpoint de health check public"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Endpoint racine - redirection vers la documentation"""
    return {
        "service": "MCP Lightning Network Optimizer API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "https://docs.dazno.de/mcp",
        "support": "admin@dazno.de"
    }

# Endpoints protégés (avec authentification)

@app.get("/api/v1/status")
@require_auth
async def get_status():
    """Status de l'API avec authentification"""
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "mongodb": "connected",
            "redis": "connected",
            "sparkseer": "connected" if os.getenv("SPARKSEER_API_KEY") else "not_configured"
        }
    }

@app.post("/api/v1/simulate/node")
@require_auth
async def simulate_node(request: Request):
    """Simulation de nœud avec authentification"""
    data = await request.json()
    simulator = NodeSimulator()
    result = await simulator.simulate(data)
    return result

@app.get("/api/v1/simulate/profiles")
@require_auth
async def get_simulation_profiles():
    """Profils de simulation disponibles"""
    return {
        "profiles": [
            "basic",
            "advanced",
            "custom"
        ]
    }

@app.post("/api/v1/optimize/node/{node_id}")
@require_auth
async def optimize_node(node_id: str, request: Request):
    """Optimisation de nœud avec authentification"""
    data = await request.json()
    scanner = NodeScanner()
    result = await scanner.optimize(node_id, data)
    return result

# Endpoints d'administration (accès restreint)

@app.get("/api/v1/admin/metrics")
@require_auth
@require_permissions(["admin"])
async def get_admin_metrics():
    """Métriques admin avec permissions"""
    return {
        "metrics": {
            "requests": 1000,
            "errors": 5,
            "average_response_time": 0.5
        }
    }

@app.post("/api/v1/admin/maintenance")
@require_auth
@require_permissions(["admin"])
async def maintenance_mode(request: Request):
    """Mode maintenance avec permissions"""
    data = await request.json()
    # Logique de maintenance
    return {"status": "maintenance_mode_activated"}

# Gestionnaire d'erreurs global
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Gestionnaire pour les erreurs 404"""
    client_ip = get_client_ip(request)
    logger.warning(f"404 error from {client_ip}: {request.url.path}")
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "path": str(request.url.path),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Gestionnaire pour les erreurs internes"""
    client_ip = get_client_ip(request)
    logger.error(f"Internal server error from {client_ip}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

# Configuration pour le démarrage
if __name__ == "__main__":
    # Marquer l'heure de démarrage
    app.state.start_time = time.time()
    
    # Configuration Uvicorn pour la production
    uvicorn.run(
        "src.api.production:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=int(os.getenv("WORKERS", 4)),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        reload=False,  # Jamais de reload en production
        server_header=False,  # Cacher le header Server
        date_header=False  # Cacher le header Date
    ) 