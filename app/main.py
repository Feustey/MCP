# app/main.py
"""
Application FastAPI principale optimisée pour MCP
Inclut middleware de performance, monitoring et gestion d'erreurs avancée

Dernière mise à jour: 7 mai 2025
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvloop

# Configuration et logging optimisés
from config import settings
from src.logging_config import get_logger, log_performance, log_security_event
from src.performance_metrics import get_app_metrics, record_request, measure_time
from src.circuit_breaker import CircuitBreakerRegistry
from src.redis_operations_optimized import get_redis_client, get_redis_from_pool
from src.rag_optimized import rag_workflow
from src.exceptions import (
    MCPBaseException, 
    ExceptionHandler, 
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NetworkError,
    create_error_context
)

# Routes
from app.routes.health import router as health_router
from app.routes.api import router as api_router
from app.routes.metrics import router as metrics_router

logger = get_logger(__name__)
app_metrics = get_app_metrics()
exception_handler = ExceptionHandler()

# Client Redis global
redis_client = get_redis_from_pool()


class PerformanceMiddleware:
    """Middleware de mesure de performance"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"
        
        # Ajoute l'ID de requête aux headers
        request.state.request_id = request_id
        
        # Log de la requête entrante
        logger.info("Requête entrante",
                   method=request.method,
                   url=str(request.url),
                   request_id=request_id,
                   user_agent=request.headers.get("user-agent", "unknown"))
        
        try:
            response = await call_next(request)
            success = response.status_code < 400
            
        except Exception as e:
            # Gère les exceptions non catchées
            logger.error("Exception non gérée dans middleware",
                        error=str(e),
                        request_id=request_id)
            
            # Convertit en exception MCP
            context = create_error_context(
                operation="http_request",
                component="middleware",
                request_id=request_id,
                method=request.method,
                url=str(request.url)
            )
            
            mcp_error = exception_handler.handle_exception(e, context, reraise=False)
            
            response = JSONResponse(
                status_code=500,
                content={
                    "error": mcp_error.to_dict(),
                    "request_id": request_id
                }
            )
            success = False
        
        finally:
            # Calcule la durée
            duration_ms = (time.time() - start_time) * 1000
            
            # Ajoute les headers de performance
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Enregistre les métriques
            record_request(success, duration_ms)
            log_performance("http_request", duration_ms,
                          method=request.method,
                          status_code=response.status_code,
                          success=success)
            
            # Log de la réponse
            logger.info("Réponse sortante",
                       status_code=response.status_code,
                       duration_ms=duration_ms,
                       request_id=request_id,
                       success=success)
        
        return response


class SecurityMiddleware:
    """Middleware de sécurité"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        # Headers de sécurité
        response = await call_next(request)
        
        # Ajoute les headers de sécurité
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    logger.info("Démarrage de l'application MCP",
               environment=settings.environment,
               version=settings.version)
    
    try:
        # Configure uvloop pour de meilleures performances
        if hasattr(uvloop, 'install'):
            uvloop.install()
            logger.info("uvloop installé pour optimisation des performances")
        
        # Test de connexion Redis
        try:
            redis_client.ping()
            logger.info("Connexion Redis testée avec succès",
                       host=settings.redis.host,
                       port=settings.redis.port)
        except Exception as e:
            logger.error("Erreur de connexion Redis",
                        error=str(e),
                        host=settings.redis.host,
                        port=settings.redis.port)
            raise
        
        # Initialise le système RAG
        await rag_workflow.initialize()
        logger.info("Système RAG initialisé")
        
        # Démarre la collecte de métriques
        await app_metrics.start_collection()
        logger.info("Collecte de métriques démarrée")
        
        # L'application est prête
        logger.info("Application MCP démarrée avec succès")
        
        yield
        
    except Exception as e:
        logger.error("Erreur lors du démarrage", error=str(e))
        raise
    
    finally:
        # Nettoyage
        logger.info("Arrêt de l'application MCP")
        
        try:
            await app_metrics.stop_collection()
            await rag_workflow.close()
            logger.info("Nettoyage terminé")
        except Exception as e:
            logger.error("Erreur lors du nettoyage", error=str(e))


# Création de l'application
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Système d'optimisation Lightning Network avec IA et RAG",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.security.allowed_hosts)
app.add_middleware(PerformanceMiddleware)
app.add_middleware(SecurityMiddleware)

# Routes
app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
app.include_router(api_router, prefix="/api/v1", tags=["api"])


# Gestionnaire global d'exceptions
@app.exception_handler(MCPBaseException)
async def mcp_exception_handler(request: Request, exc: MCPBaseException):
    """Gestionnaire pour les exceptions MCP"""
    
    # Log sécurisé pour les erreurs d'auth
    if isinstance(exc, (AuthenticationError, AuthorizationError)):
        log_security_event(
            "authentication_error",
            request_id=getattr(request.state, 'request_id', 'unknown'),
            ip=request.client.host if request.client else 'unknown',
            url=str(request.url),
            error_type=exc.__class__.__name__
        )
    
    # Détermine le code de statut HTTP
    status_code = 500
    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, AuthorizationError):
        status_code = 403
    elif isinstance(exc, NetworkError):
        status_code = 502
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.to_dict(),
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire pour les exceptions HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code
            },
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Gestionnaire pour toutes les autres exceptions"""
    
    context = create_error_context(
        operation="http_request",
        component="global_handler",
        request_id=getattr(request.state, 'request_id', 'unknown'),
        method=request.method,
        url=str(request.url)
    )
    
    mcp_error = exception_handler.handle_exception(exc, context, reraise=False)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": mcp_error.to_dict(),
            "request_id": getattr(request.state, 'request_id', 'unknown')
        }
    )


@app.get("/")
async def root():
    """Endpoint racine avec informations système"""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "docs_url": "/docs" if not settings.is_production else None
    }


@app.get("/info")
async def app_info():
    """Informations détaillées sur l'application"""
    
    # Statistiques des circuit breakers
    cb_stats = CircuitBreakerRegistry.get_stats_summary()
    
    # Métriques de l'application
    metrics_summary = app_metrics.get_summary()
    
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "system": {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - getattr(app.state, 'start_time', time.time())
        },
        "metrics": metrics_summary,
        "circuit_breakers": cb_stats,
        "configuration": {
            "performance": {
                "max_workers": settings.performance.max_workers,
                "rate_limit_requests": settings.performance.rate_limit_requests,
                "default_timeout": settings.performance.default_timeout
            },
            "redis": {
                "max_connections": settings.redis.max_connections,
                "socket_timeout": settings.redis.socket_timeout
            }
        }
    }


# Configuration OpenAPI personnalisée pour la production
if not settings.is_production:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Ajoute des informations de sécurité
        openapi_schema["info"]["x-api-version"] = settings.version
        openapi_schema["info"]["x-environment"] = settings.environment
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


# Points de santé pour le monitoring
@app.get("/health/ready")
async def readiness_probe():
    """Probe de disponibilité pour Kubernetes/Docker"""
    try:
        # Vérifie Redis
        redis_health = await redis_client.ping()
        
        if redis_health != "PONG":
            raise HTTPException(status_code=503, detail="Redis non disponible")
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis": redis_health
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service non prêt: {str(e)}")


@app.get("/health/live")
async def liveness_probe():
    """Probe de vitalité pour Kubernetes/Docker"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - getattr(app.state, 'start_time', time.time())
    }


# Initialisation du timestamp de démarrage
if not hasattr(app.state, 'start_time'):
    app.state.start_time = time.time()

# Log final de configuration
logger.info("Configuration de l'application terminée",
           debug=settings.debug,
           environment=settings.environment,
           cors_origins=settings.get_cors_origins())

# Permet de lancer l'app avec `python app/main.py` pour le développement
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True # Recharge automatiquement lors des modifications du code
    ) 