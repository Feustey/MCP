"""
Routes de santé et monitoring pour MCP
Vérifications complètes du système avec métriques détaillées

Dernière mise à jour: 9 janvier 2025
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from config import settings
from src.logging_config import get_logger
from src.performance_metrics import get_app_metrics
from src.circuit_breaker import CircuitBreakerRegistry
from src.redis_operations_optimized import redis_ops, get_redis_client
from src.rag_optimized import rag_workflow
from src.exceptions import exception_handler
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


async def get_system_health() -> Dict[str, Any]:
    """Vérifie la santé globale du système"""
    health_status = {
        "overall": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    failed_components = []
    
    # Vérification Redis
    try:
        redis_health = await redis_ops.health_check()
        health_status["components"]["redis"] = redis_health
        if redis_health["status"] != "healthy":
            failed_components.append("redis")
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        failed_components.append("redis")
    
    # Vérification RAG (basique)
    try:
        if rag_workflow._initialized:
            health_status["components"]["rag"] = {
                "status": "healthy",
                "initialized": True
            }
        else:
            health_status["components"]["rag"] = {
                "status": "unhealthy",
                "initialized": False
            }
            failed_components.append("rag")
    except Exception as e:
        health_status["components"]["rag"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        failed_components.append("rag")
    
    # État global
    if failed_components:
        health_status["overall"] = "degraded" if len(failed_components) < 2 else "unhealthy"
        health_status["failed_components"] = failed_components
    
    return health_status


@router.get("/")
async def health_check():
    """Vérification de santé basique"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.version
    }


@router.get("/detailed")
async def detailed_health_check():
    """Vérification de santé détaillée"""
    health_status = await get_system_health()
    
    # Ajoute les métriques de l'application
    app_metrics = get_app_metrics()
    metrics_summary = app_metrics.get_summary()
    health_status["metrics"] = metrics_summary
    
    # Ajoute les statistiques des circuit breakers
    cb_stats = CircuitBreakerRegistry.get_stats_summary()
    health_status["circuit_breakers"] = cb_stats
    
    # Ajoute les statistiques d'erreurs
    error_stats = exception_handler.get_error_stats()
    health_status["errors"] = error_stats
    
    # Statut HTTP selon la santé
    if health_status["overall"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    elif health_status["overall"] == "degraded":
        return JSONResponse(status_code=206, content=health_status)
    
    return health_status


@router.get("/components")
async def components_health():
    """Santé individuelle des composants"""
    components = {}
    
    # Redis
    try:
        redis_health = await redis_ops.health_check()
        components["redis"] = redis_health
    except Exception as e:
        components["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Configuration
    try:
        components["configuration"] = {
            "status": "healthy",
            "environment": settings.environment,
            "debug": settings.debug,
            "redis_url": settings.get_redis_url()[:20] + "..." if len(settings.get_redis_url()) > 20 else settings.get_redis_url(),
            "database_configured": bool(settings.database.url)
        }
    except Exception as e:
        components["configuration"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Circuit Breakers
    try:
        cb_summary = CircuitBreakerRegistry.get_stats_summary()
        open_breakers = cb_summary["states"].get("open", 0)
        components["circuit_breakers"] = {
            "status": "healthy" if open_breakers == 0 else "degraded",
            "total": cb_summary["total_breakers"],
            "open": open_breakers,
            "closed": cb_summary["states"].get("closed", 0),
            "half_open": cb_summary["states"].get("half_open", 0)
        }
    except Exception as e:
        components["circuit_breakers"] = {
            "status": "error",
            "error": str(e)
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "components": components
    }


@router.get("/metrics")
async def health_metrics():
    """Métriques de santé et performance"""
    app_metrics = get_app_metrics()
    
    try:
        # Métriques de base
        metrics_data = app_metrics.get_all_metrics()
        
        # Métriques système
        system_metrics = {}
        try:
            import psutil
            system_metrics = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        except ImportError:
            system_metrics = {"error": "psutil non disponible"}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "application_metrics": metrics_data,
            "system_metrics": system_metrics,
            "circuit_breakers": CircuitBreakerRegistry.get_all_metrics()
        }
        
    except Exception as e:
        logger.error("Erreur collecte métriques santé", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur métriques: {str(e)}")


@router.post("/reset")
async def reset_health_stats():
    """Remet à zéro les statistiques de santé"""
    try:
        # Reset des métriques d'application
        app_metrics = get_app_metrics()
        # Note: ajouterions une méthode reset si nécessaire
        
        # Reset des statistiques d'erreurs
        exception_handler.clear_stats()
        
        # Reset des circuit breakers si demandé
        # CircuitBreakerRegistry.reset_all()  # Décommenter si nécessaire
        
        return {
            "status": "success",
            "message": "Statistiques de santé remises à zéro",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Erreur reset statistiques", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur reset: {str(e)}")


# Endpoints Kubernetes/Docker
@router.get("/ready")
async def readiness_probe():
    """Probe de disponibilité Kubernetes"""
    health_status = await get_system_health()
    
    if health_status["overall"] == "unhealthy":
        raise HTTPException(status_code=503, detail="Service non prêt")
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_probe():
    """Probe de vitalité Kubernetes"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time()  # Timestamp simple pour éviter les dépendances
    }


@router.get("/health")
async def health_check():
    """
    Vérifie la santé globale de l'application
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "production"
    }


@router.get("/health/redis")
async def check_redis_health():
    """
    Vérifie la santé de la connexion Redis
    """
    try:
        redis = get_redis_client()
        redis.ping()
        info = redis.info()
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human")
        }
    except Exception as e:
        logger.error("Erreur de santé Redis", error=str(e))
        raise HTTPException(
            status_code=503,
            detail=f"Redis health check failed: {str(e)}"
        ) 