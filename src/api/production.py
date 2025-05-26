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

# Création de l'application FastAPI
app = FastAPI(
    title="MCP Lightning Network Optimizer API",
    description="API sécurisée pour l'optimisation des nœuds Lightning Network",
    version="1.0.0",
    docs_url=None,  # Désactiver Swagger en production
    redoc_url=None,  # Désactiver ReDoc en production
    openapi_url=None,  # Désactiver OpenAPI en production
    lifespan=lifespan
)

# Configuration des origines autorisées
ALLOWED_ORIGINS = [
    "https://app.dazno.de",
    "https://dazno.de",
    "https://www.dazno.de"
]

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

@app.get("/", include_in_schema=False)
async def root():
    """Endpoint racine - redirection vers la documentation"""
    return {
        "service": "MCP Lightning Network Optimizer API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "https://docs.dazno.de/mcp",
        "support": "admin@dazno.de"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Vérification de l'état de l'API"""
    try:
        # Vérifications de base
        checks = {
            "api": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        }
        
        # Vérification optionnelle des services externes
        # (peut être désactivée pour éviter les timeouts)
        
        return {
            "status": "healthy",
            "checks": checks,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/status", tags=["Health"])
async def status():
    """Status détaillé (pour monitoring interne)"""
    return {
        "service": "MCP API",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "authentication": True,
            "rate_limiting": True,
            "cors_enabled": True,
            "monitoring": True
        }
    }

# Endpoints protégés par authentification

@app.get("/api/v1/simulate/profiles", tags=["Simulation"])
async def get_simulation_profiles(auth: Dict[str, Any] = Depends(require_auth)):
    """Récupère les profils de simulation disponibles"""
    try:
        simulator = app.state.simulator
        profiles = simulator.get_available_profiles()
        
        logger.info(f"Profiles requested by user {auth['user']['sub']}")
        
        return {
            "profiles": profiles,
            "count": len(profiles),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting simulation profiles: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve simulation profiles"
        )

@app.post("/api/v1/simulate/node", tags=["Simulation"])
async def simulate_node(
    request_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(require_permissions("simulate"))
):
    """Simule le comportement d'un nœud Lightning"""
    try:
        simulator = app.state.simulator
        
        # Validation des données d'entrée
        if "profile" not in request_data:
            raise HTTPException(
                status_code=400,
                detail="Profile parameter is required"
            )
        
        profile = request_data["profile"]
        parameters = request_data.get("parameters", {})
        
        # Exécuter la simulation
        result = simulator.simulate_node_behavior(profile, parameters)
        
        logger.info(
            f"Node simulation executed: profile={profile} "
            f"by user={auth['user']['sub']}"
        )
        
        return {
            "simulation_id": result.get("simulation_id"),
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "user": auth['user']['sub']
        }
        
    except Exception as e:
        logger.error(f"Error in node simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Simulation failed"
        )

@app.post("/api/v1/optimize/node", tags=["Optimization"])
async def optimize_node(
    request_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(require_permissions("optimize"))
):
    """Optimise la configuration d'un nœud"""
    try:
        # Validation des données
        if "node_id" not in request_data:
            raise HTTPException(
                status_code=400,
                detail="node_id parameter is required"
            )
        
        node_id = request_data["node_id"]
        current_config = request_data.get("current_config", {})
        
        # Évaluer le nœud actuel
        evaluation = evaluate_node(node_id, current_config)
        
        logger.info(
            f"Node optimization requested: node_id={node_id} "
            f"by user={auth['user']['sub']}"
        )
        
        return {
            "node_id": node_id,
            "evaluation": evaluation,
            "recommendations": evaluation.get("recommendations", []),
            "timestamp": datetime.now().isoformat(),
            "user": auth['user']['sub']
        }
        
    except Exception as e:
        logger.error(f"Error in node optimization: {e}")
        raise HTTPException(
            status_code=500,
            detail="Optimization failed"
        )

@app.get("/api/v1/scan/node/{node_id}", tags=["Scanning"])
async def scan_node(
    node_id: str,
    auth: Dict[str, Any] = Depends(require_permissions("scan"))
):
    """Scan des informations d'un nœud"""
    try:
        scanner = app.state.scanner
        
        # Valider le format du node_id
        if len(node_id) != 66:  # Format pubkey standard
            raise HTTPException(
                status_code=400,
                detail="Invalid node_id format"
            )
        
        # Exécuter le scan
        scan_result = scanner.scan_node(node_id)
        
        logger.info(
            f"Node scan executed: node_id={node_id} "
            f"by user={auth['user']['sub']}"
        )
        
        return {
            "node_id": node_id,
            "scan_result": scan_result,
            "timestamp": datetime.now().isoformat(),
            "user": auth['user']['sub']
        }
        
    except Exception as e:
        logger.error(f"Error in node scan: {e}")
        raise HTTPException(
            status_code=500,
            detail="Node scan failed"
        )

# Endpoints administrateur

@app.get("/api/v1/admin/metrics", tags=["Admin"])
async def get_admin_metrics(auth: Dict[str, Any] = Depends(require_permissions("admin"))):
    """Métriques administrateur"""
    try:
        # Récupérer les métriques système
        metrics = {
            "security": {
                "failed_attempts": len(security_manager.failed_attempts),
                "blocked_ips": len(security_manager.blocked_ips),
                "blocked_tokens": len(security_manager.blocked_tokens),
                "rate_limits": len(security_manager.rate_limits)
            },
            "api": {
                "version": "1.0.0",
                "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
                "environment": os.getenv("ENVIRONMENT", "production")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Admin metrics accessed by user {auth['user']['sub']}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting admin metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics"
        )

@app.post("/api/v1/admin/security/block-ip", tags=["Admin"])
async def block_ip(
    request_data: Dict[str, Any],
    auth: Dict[str, Any] = Depends(require_permissions("admin"))
):
    """Bloque une adresse IP"""
    try:
        ip_address = request_data.get("ip_address")
        reason = request_data.get("reason", "Manual block by admin")
        
        if not ip_address:
            raise HTTPException(
                status_code=400,
                detail="ip_address parameter is required"
            )
        
        # Bloquer l'IP
        security_manager.blocked_ips.add(ip_address)
        
        logger.warning(
            f"IP {ip_address} blocked manually by admin {auth['user']['sub']}: {reason}"
        )
        
        return {
            "status": "success",
            "message": f"IP {ip_address} has been blocked",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error blocking IP: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to block IP"
        )

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