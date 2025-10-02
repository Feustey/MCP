"""
Routes de métriques et monitoring pour MCP
Export Prometheus, dashboard et analyses de performance

Dernière mise à jour: 9 janvier 2025
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse

from config import settings
from src.logging_config import get_logger
from src.performance_metrics import get_app_metrics
from src.circuit_breaker import CircuitBreakerRegistry
from src.redis_operations_optimized import redis_ops, get_redis_client
from src.exceptions import exception_handler
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/")
async def metrics_overview():
    """Vue d'ensemble des métriques"""
    app_metrics = get_app_metrics()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "summary": app_metrics.get_summary(),
        "endpoints": {
            "detailed": "/metrics/detailed",
            "prometheus": "/metrics/prometheus",
            "circuit_breakers": "/metrics/circuit-breakers",
            "errors": "/metrics/errors",
            "performance": "/metrics/performance",
            "redis": "/metrics/redis"
        }
    }


@router.get("/detailed")
async def detailed_metrics():
    """Métriques détaillées de l'application"""
    app_metrics = get_app_metrics()
    
    try:
        # Métriques de l'application
        all_metrics = app_metrics.get_all_metrics()
        
        # Métriques système si disponibles
        system_metrics = {}
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Mémoire
            memory = psutil.virtual_memory()
            
            # Disque
            disk = psutil.disk_usage('/')
            
            # Réseau
            network = psutil.net_io_counters()
            
            system_metrics = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except ImportError:
            system_metrics = {"error": "psutil non disponible"}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "application_metrics": all_metrics,
            "system_metrics": system_metrics,
            "collection_info": {
                "component": app_metrics.component_name,
                "metrics_count": len(all_metrics),
                "collection_enabled": True
            }
        }
        
    except Exception as e:
        logger.error("Erreur collecte métriques détaillées", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur métriques: {str(e)}")


@router.get("/prometheus",
    response_class=PlainTextResponse,
    summary="Export Métriques Prometheus",
    description="Export des métriques au format Prometheus pour intégration Grafana",
    responses={
        200: {
            "description": "Métriques au format Prometheus",
            "content": {
                "text/plain": {
                    "example": """# Application Metrics
mcp_requests_total 1234
mcp_requests_failed 23
mcp_response_time_ms 145.2

# Circuit Breaker Metrics
circuit_breaker_state{name="redis"} 0
circuit_breaker_requests_total{name="redis"} 5678

# System Metrics
system_cpu_percent 45.2
system_memory_percent 62.8
"""
                }
            }
        },
        500: {"description": "Erreur lors de l'export"}
    }
)
async def prometheus_metrics():
    """
    **📊 Export Métriques Prometheus**

    Exporte toutes les métriques de l'application au format Prometheus
    pour monitoring et visualisation dans Grafana.

    **Métriques Exportées:**
    - **Application**: Requêtes, erreurs, temps de réponse
    - **Circuit Breakers**: État, taux d'échec, durée moyenne
    - **Système**: CPU, mémoire, disque, réseau
    - **Redis**: Hits/misses cache, connexions

    **Utilisation avec Prometheus:**
    ```yaml
    scrape_configs:
      - job_name: 'mcp-api'
        static_configs:
          - targets: ['app.dazno.de:8000']
        metrics_path: '/metrics/prometheus'
    ```

    **Intégration Grafana:**
    Utilisez ce endpoint comme source de données Prometheus
    pour créer des dashboards de monitoring.
    """
    try:
        app_metrics = get_app_metrics()
        
        # Export au format Prometheus
        prometheus_output = app_metrics.export_prometheus_format()
        
        # Ajoute les métriques des circuit breakers
        cb_registry = CircuitBreakerRegistry()
        cb_metrics = []
        
        for name, breaker in cb_registry.get_all().items():
            stats = breaker.get_stats()
            
            # État du circuit breaker (0=closed, 1=half_open, 2=open)
            state_value = {"closed": 0, "half_open": 1, "open": 2}[stats["state"]]
            cb_metrics.append(f"circuit_breaker_state{{name=\"{name}\"}} {state_value}")
            
            # Métriques de base
            cb_metrics.append(f"circuit_breaker_requests_total{{name=\"{name}\"}} {stats['stats']['total_requests']}")
            cb_metrics.append(f"circuit_breaker_failures_total{{name=\"{name}\"}} {stats['stats']['failure_count']}")
            cb_metrics.append(f"circuit_breaker_success_total{{name=\"{name}\"}} {stats['stats']['success_count']}")
            cb_metrics.append(f"circuit_breaker_failure_rate{{name=\"{name}\"}} {stats['stats']['failure_rate']}")
            cb_metrics.append(f"circuit_breaker_avg_duration_ms{{name=\"{name}\"}} {stats['stats']['average_duration_ms']}")
        
        # Combine les métriques
        if cb_metrics:
            prometheus_output += "\n\n# Circuit Breaker Metrics\n"
            prometheus_output += "\n".join(cb_metrics)
        
        # Ajoute les métriques système si disponibles
        try:
            import psutil
            
            system_metrics = [
                f"system_cpu_percent {psutil.cpu_percent()}",
                f"system_memory_percent {psutil.virtual_memory().percent}",
                f"system_disk_percent {(psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100}"
            ]
            
            prometheus_output += "\n\n# System Metrics\n"
            prometheus_output += "\n".join(system_metrics)
            
        except ImportError:
            pass
        
        return prometheus_output
        
    except Exception as e:
        logger.error("Erreur export Prometheus", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur export Prometheus: {str(e)}")


@router.get("/circuit-breakers")
async def circuit_breaker_metrics():
    """Métriques des circuit breakers"""
    try:
        cb_stats = CircuitBreakerRegistry.get_stats_summary()
        cb_details = CircuitBreakerRegistry.get_all_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": cb_stats,
            "details": cb_details,
            "health_status": {
                "total_open": cb_stats["states"].get("open", 0),
                "total_degraded": cb_stats["states"].get("half_open", 0),
                "total_healthy": cb_stats["states"].get("closed", 0),
                "overall_health": "healthy" if cb_stats["states"].get("open", 0) == 0 else "degraded"
            }
        }
        
    except Exception as e:
        logger.error("Erreur métriques circuit breakers", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur circuit breakers: {str(e)}")


@router.get("/errors")
async def error_metrics():
    """Métriques et statistiques d'erreurs"""
    try:
        error_stats = exception_handler.get_error_stats()
        
        # Analyse des tendances d'erreurs
        recent_errors = error_stats.get("recent_errors", [])
        error_trend = {}
        
        if recent_errors:
            # Groupe les erreurs par heure
            now = datetime.utcnow()
            for i in range(24):  # 24 dernières heures
                hour_start = now - timedelta(hours=i+1)
                hour_end = now - timedelta(hours=i)
                
                hour_errors = [
                    err for err in recent_errors
                    if hour_start <= datetime.fromisoformat(err["timestamp"]) < hour_end
                ]
                
                error_trend[f"hour_{i}"] = len(hour_errors)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": error_stats,
            "trends": {
                "last_24_hours": error_trend,
                "error_rate_24h": len(recent_errors)
            },
            "health_assessment": {
                "status": "healthy" if error_stats.get("total_errors", 0) < 100 else "degraded",
                "recommendation": "Système stable" if error_stats.get("total_errors", 0) < 50 
                                else "Surveiller les erreurs récurrentes"
            }
        }
        
    except Exception as e:
        logger.error("Erreur métriques d'erreurs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur métriques erreurs: {str(e)}")


@router.get("/performance")
async def performance_metrics(
    window_minutes: int = Query(60, description="Fenêtre de temps en minutes", ge=1, le=1440)
):
    """Métriques de performance sur une fenêtre de temps"""
    try:
        app_metrics = get_app_metrics()
        
        # Métriques de performance
        perf_data = {
            "window_minutes": window_minutes,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": app_metrics.get_summary()
        }
        
        # Analyse des timers et histogrammes
        all_metrics = app_metrics.get_all_metrics()
        
        performance_analysis = {}
        for name, metric in all_metrics.items():
            if metric.get("type") in ["timer", "histogram"]:
                stats = metric.get("statistics", {})
                percentiles = metric.get("percentiles", {})
                
                performance_analysis[name] = {
                    "avg_duration_ms": stats.get("mean", 0),
                    "min_duration_ms": stats.get("min", 0),
                    "max_duration_ms": stats.get("max", 0),
                    "p95_duration_ms": percentiles.get("p95", 0),
                    "p99_duration_ms": percentiles.get("p99", 0),
                    "total_operations": stats.get("count", 0)
                }
        
        perf_data["performance_analysis"] = performance_analysis
        
        # Recommandations de performance
        recommendations = []
        summary = perf_data["summary"]
        
        if summary.get("avg_response_time_ms", 0) > 1000:
            recommendations.append("Temps de réponse élevé - optimiser les requêtes")
        
        if summary.get("error_rate", 0) > 5:
            recommendations.append("Taux d'erreur élevé - vérifier la stabilité")
        
        if not recommendations:
            recommendations.append("Performance dans les normes")
        
        perf_data["recommendations"] = recommendations
        
        return perf_data
        
    except Exception as e:
        logger.error("Erreur métriques performance", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur métriques performance: {str(e)}")


@router.get("/redis")
async def redis_metrics():
    """
    Retourne les métriques Redis
    """
    try:
        redis = get_redis_client()
        info = redis.info()
        
        return {
            "memory": {
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "used_memory_lua": info.get("used_memory_lua"),
                "used_memory_scripts": info.get("used_memory_scripts"),
            },
            "clients": {
                "connected_clients": info.get("connected_clients"),
                "blocked_clients": info.get("blocked_clients"),
                "tracking_clients": info.get("tracking_clients"),
            },
            "stats": {
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "total_net_input_bytes": info.get("total_net_input_bytes"),
                "total_net_output_bytes": info.get("total_net_output_bytes"),
            },
            "persistence": {
                "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save"),
                "rdb_last_save_time": info.get("rdb_last_save_time"),
            },
            "cpu": {
                "used_cpu_sys": info.get("used_cpu_sys"),
                "used_cpu_user": info.get("used_cpu_user"),
                "used_cpu_sys_children": info.get("used_cpu_sys_children"),
                "used_cpu_user_children": info.get("used_cpu_user_children"),
            }
        }
    except Exception as e:
        logger.error("Erreur récupération métriques Redis", error=str(e))
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/dashboard")
async def metrics_dashboard():
    """Dashboard consolidé des métriques"""
    try:
        # Collecte toutes les métriques importantes
        app_metrics = get_app_metrics()
        summary = app_metrics.get_summary()
        
        # Circuit breakers
        cb_stats = CircuitBreakerRegistry.get_stats_summary()
        
        # Erreurs
        error_stats = exception_handler.get_error_stats()
        
        # Redis
        redis_health = await redis_ops.health_check()
        cache_stats = await redis_ops.get_stats()
        
        # Calcul du score de santé global
        health_score = 100
        health_issues = []
        
        # Pénalités
        if summary.get("error_rate", 0) > 5:
            health_score -= 20
            health_issues.append("Taux d'erreur élevé")
        
        if cb_stats["states"].get("open", 0) > 0:
            health_score -= 30
            health_issues.append("Circuit breakers ouverts")
        
        if redis_health.get("status") != "healthy":
            health_score -= 25
            health_issues.append("Redis dégradé")
        
        if cache_stats.error_rate > 10:
            health_score -= 15
            health_issues.append("Cache instable")
        
        if summary.get("avg_response_time_ms", 0) > 2000:
            health_score -= 10
            health_issues.append("Temps de réponse lent")
        
        health_score = max(0, health_score)
        
        # Statut global
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 70:
            health_status = "good"
        elif health_score >= 50:
            health_status = "degraded"
        else:
            health_status = "critical"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "health_status": health_status,
            "health_issues": health_issues,
            "system_overview": {
                "service": settings.app_name,
                "version": settings.version,
                "environment": settings.environment,
                "uptime_info": summary
            },
            "performance": {
                "requests_total": summary.get("requests_total", 0),
                "error_rate": summary.get("error_rate", 0),
                "avg_response_time_ms": summary.get("avg_response_time_ms", 0),
                "response_time_p95_ms": summary.get("response_time_p95_ms", 0)
            },
            "infrastructure": {
                "redis": {
                    "status": redis_health.get("status", "unknown"),
                    "hit_rate": cache_stats.hit_rate,
                    "response_time_ms": redis_health.get("response_time_ms", 0)
                },
                "circuit_breakers": {
                    "total": cb_stats["total_breakers"],
                    "healthy": cb_stats["states"].get("closed", 0),
                    "degraded": cb_stats["states"].get("half_open", 0),
                    "failed": cb_stats["states"].get("open", 0)
                }
            },
            "errors": {
                "total_24h": len(error_stats.get("recent_errors", [])),
                "top_errors": error_stats.get("top_errors", [])[:3]
            }
        }
        
    except Exception as e:
        logger.error("Erreur dashboard métriques", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur dashboard: {str(e)}")


@router.post("/reset")
async def reset_metrics():
    """Remet à zéro certaines métriques"""
    try:
        # Reset des statistiques d'erreurs
        exception_handler.clear_stats()
        
        # Reset des statistiques Redis
        await redis_ops.reset_stats()
        
        return {
            "status": "success",
            "message": "Métriques remises à zéro",
            "timestamp": datetime.utcnow().isoformat(),
            "reset_items": [
                "Statistiques d'erreurs",
                "Statistiques Redis",
                "Cache stats"
            ]
        }
        
    except Exception as e:
        logger.error("Erreur reset métriques", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur reset: {str(e)}") 