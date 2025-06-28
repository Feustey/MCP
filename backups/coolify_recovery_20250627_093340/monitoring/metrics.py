"""
Configuration des métriques
Gestion des métriques Prometheus pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_client.metrics import MetricWrapperBase
import time
from functools import wraps
from datetime import datetime

# Configuration du logging
logger = logging.getLogger("mcp.metrics")

# Configuration des métriques
METRICS_PREFIX = "mcp_"
METRICS_LABELS = ["endpoint", "method", "status"]

# Métriques HTTP
http_requests_total = Counter(
    f"{METRICS_PREFIX}http_requests_total",
    "Total des requêtes HTTP",
    METRICS_LABELS
)

http_request_duration_seconds = Histogram(
    f"{METRICS_PREFIX}http_request_duration_seconds",
    "Durée des requêtes HTTP",
    METRICS_LABELS,
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

http_request_size_bytes = Histogram(
    f"{METRICS_PREFIX}http_request_size_bytes",
    "Taille des requêtes HTTP",
    METRICS_LABELS,
    buckets=[100, 1000, 5000, 10000, 50000]
)

http_response_size_bytes = Histogram(
    f"{METRICS_PREFIX}http_response_size_bytes",
    "Taille des réponses HTTP",
    METRICS_LABELS,
    buckets=[100, 1000, 5000, 10000, 50000]
)

# Métriques d'authentification
auth_attempts_total = Counter(
    f"{METRICS_PREFIX}auth_attempts_total",
    "Total des tentatives d'authentification",
    ["status"]
)

auth_failures_total = Counter(
    f"{METRICS_PREFIX}auth_failures_total",
    "Total des échecs d'authentification",
    ["reason"]
)

# Métriques de base de données
db_operations_total = Counter(
    f"{METRICS_PREFIX}db_operations_total",
    "Total des opérations de base de données",
    ["operation", "collection"]
)

db_operation_duration_seconds = Histogram(
    f"{METRICS_PREFIX}db_operation_duration_seconds",
    "Durée des opérations de base de données",
    ["operation", "collection"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

db_connections = Gauge(
    f"{METRICS_PREFIX}db_connections",
    "Nombre de connexions à la base de données"
)

# Métriques de cache
cache_operations_total = Counter(
    f"{METRICS_PREFIX}cache_operations_total",
    "Total des opérations de cache",
    ["operation", "status"]
)

cache_hits_total = Counter(
    f"{METRICS_PREFIX}cache_hits_total",
    "Total des hits de cache"
)

cache_misses_total = Counter(
    f"{METRICS_PREFIX}cache_misses_total",
    "Total des misses de cache"
)

cache_size_bytes = Gauge(
    f"{METRICS_PREFIX}cache_size_bytes",
    "Taille du cache en bytes"
)

# Métriques système
system_cpu_usage = Gauge(
    f"{METRICS_PREFIX}system_cpu_usage",
    "Utilisation CPU en pourcentage"
)

system_memory_usage = Gauge(
    f"{METRICS_PREFIX}system_memory_usage",
    "Utilisation mémoire en pourcentage"
)

system_disk_usage = Gauge(
    f"{METRICS_PREFIX}system_disk_usage",
    "Utilisation disque en pourcentage"
)

# Métriques d'application
app_uptime_seconds = Gauge(
    f"{METRICS_PREFIX}app_uptime_seconds",
    "Temps de fonctionnement de l'application"
)

app_requests_in_progress = Gauge(
    f"{METRICS_PREFIX}app_requests_in_progress",
    "Nombre de requêtes en cours"
)

app_error_total = Counter(
    f"{METRICS_PREFIX}app_error_total",
    "Total des erreurs de l'application",
    ["type"]
)

def track_request_metrics(func):
    """Décorateur pour suivre les métriques des requêtes"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        request = kwargs.get("request")
        
        # Labels de base
        labels = {
            "endpoint": request.url.path if request else "unknown",
            "method": request.method if request else "unknown",
            "status": "200"  # Par défaut
        }
        
        try:
            # Incrémenter les requêtes en cours
            app_requests_in_progress.inc()
            
            # Exécuter la fonction
            response = await func(*args, **kwargs)
            
            # Mettre à jour le statut
            labels["status"] = str(response.status_code)
            
            return response
            
        except Exception as e:
            # En cas d'erreur
            labels["status"] = "500"
            app_error_total.labels(type=type(e).__name__).inc()
            raise
            
        finally:
            # Calculer la durée
            duration = time.time() - start_time
            
            # Mettre à jour les métriques
            http_requests_total.labels(**labels).inc()
            http_request_duration_seconds.labels(**labels).observe(duration)
            
            # Décrémenter les requêtes en cours
            app_requests_in_progress.dec()
    
    return wrapper

def track_db_operation(operation: str, collection: str):
    """Décorateur pour suivre les métriques des opérations DB"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Incrémenter les connexions
                db_connections.inc()
                
                # Exécuter l'opération
                result = await func(*args, **kwargs)
                
                # Mettre à jour les métriques
                db_operations_total.labels(
                    operation=operation,
                    collection=collection
                ).inc()
                
                return result
                
            except Exception as e:
                # En cas d'erreur
                app_error_total.labels(type=type(e).__name__).inc()
                raise
                
            finally:
                # Calculer la durée
                duration = time.time() - start_time
                
                # Mettre à jour les métriques
                db_operation_duration_seconds.labels(
                    operation=operation,
                    collection=collection
                ).observe(duration)
                
                # Décrémenter les connexions
                db_connections.dec()
        
        return wrapper
    return decorator

def track_cache_operation(operation: str):
    """Décorateur pour suivre les métriques des opérations de cache"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Exécuter l'opération
                result = await func(*args, **kwargs)
                
                # Mettre à jour les métriques
                cache_operations_total.labels(
                    operation=operation,
                    status="success"
                ).inc()
                
                if operation == "get":
                    if result is not None:
                        cache_hits_total.inc()
                    else:
                        cache_misses_total.inc()
                
                return result
                
            except Exception as e:
                # En cas d'erreur
                cache_operations_total.labels(
                    operation=operation,
                    status="error"
                ).inc()
                app_error_total.labels(type=type(e).__name__).inc()
                raise
        
        return wrapper
    return decorator

def update_system_metrics():
    """Met à jour les métriques système"""
    try:
        import psutil
        
        # CPU
        system_cpu_usage.set(psutil.cpu_percent())
        
        # Mémoire
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)
        
        # Disque
        disk = psutil.disk_usage("/")
        system_disk_usage.set(disk.percent)
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {str(e)}")

def get_metrics_summary() -> Dict[str, Any]:
    """Récupère un résumé des métriques"""
    return {
        "http": {
            "requests_total": http_requests_total._value.get(),
            "requests_in_progress": app_requests_in_progress._value.get(),
            "errors_total": app_error_total._value.get()
        },
        "database": {
            "operations_total": db_operations_total._value.get(),
            "connections": db_connections._value.get()
        },
        "cache": {
            "operations_total": cache_operations_total._value.get(),
            "hits_total": cache_hits_total._value.get(),
            "misses_total": cache_misses_total._value.get()
        },
        "system": {
            "cpu_usage": system_cpu_usage._value.get(),
            "memory_usage": system_memory_usage._value.get(),
            "disk_usage": system_disk_usage._value.get()
        },
        "application": {
            "uptime_seconds": app_uptime_seconds._value.get()
        }
    } 