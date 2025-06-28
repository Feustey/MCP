from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Métriques pour les requêtes RAG
RAG_QUERIES_TOTAL = Counter(
    'rag_queries_total',
    'Nombre total de requêtes RAG',
    ['model', 'status']
)

RAG_QUERY_LATENCY = Histogram(
    'rag_query_latency_seconds',
    'Latence des requêtes RAG',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

RAG_EMBEDDING_LATENCY = Histogram(
    'rag_embedding_latency_seconds',
    'Latence des générations d\'embeddings',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

RAG_CACHE_HITS = Counter(
    'rag_cache_hits_total',
    'Nombre total de hits du cache',
    ['operation']
)

RAG_CACHE_MISSES = Counter(
    'rag_cache_misses_total',
    'Nombre total de misses du cache',
    ['operation']
)

RAG_ERRORS = Counter(
    'rag_errors_total',
    'Nombre total d\'erreurs',
    ['type', 'model']
)

RAG_ACTIVE_CONNECTIONS = Gauge(
    'rag_active_connections',
    'Nombre de connexions actives',
    ['type']
)

def track_metrics(metric_type: str = 'query'):
    """Décorateur pour suivre les métriques des fonctions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            model = kwargs.get('model', 'default')
            
            try:
                result = await func(*args, **kwargs)
                
                # Enregistrer les métriques de succès
                if metric_type == 'query':
                    RAG_QUERIES_TOTAL.labels(model=model, status='success').inc()
                    RAG_QUERY_LATENCY.labels(model=model).observe(time.time() - start_time)
                elif metric_type == 'embedding':
                    RAG_EMBEDDING_LATENCY.labels(model=model).observe(time.time() - start_time)
                
                return result
                
            except Exception as e:
                # Enregistrer les métriques d'erreur
                RAG_ERRORS.labels(type=type(e).__name__, model=model).inc()
                RAG_QUERIES_TOTAL.labels(model=model, status='error').inc()
                logger.error(f"Erreur dans {func.__name__}: {e}")
                raise
                
        return wrapper
    return decorator

def track_cache_operation(operation: str):
    """Décorateur pour suivre les opérations de cache."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if result is not None:
                    RAG_CACHE_HITS.labels(operation=operation).inc()
                else:
                    RAG_CACHE_MISSES.labels(operation=operation).inc()
                return result
            except Exception as e:
                logger.error(f"Erreur dans l'opération de cache {operation}: {e}")
                raise
        return wrapper
    return decorator 