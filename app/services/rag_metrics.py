"""
Métriques Prometheus détaillées pour le système RAG MCP
Permet un monitoring granulaire des performances et de la qualité
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from functools import wraps
import time
from typing import Callable, Any

logger = logging.getLogger(__name__)

# ============================================================================
# MÉTRIQUES DE REQUÊTES RAG
# ============================================================================

rag_requests_total = Counter(
    'rag_requests_total',
    'Total RAG requests',
    ['endpoint', 'cache_status', 'status', 'model']
)

rag_requests_in_progress = Gauge(
    'rag_requests_in_progress',
    'Number of RAG requests currently in progress',
    ['endpoint']
)

# ============================================================================
# MÉTRIQUES DE PERFORMANCE
# ============================================================================

rag_processing_duration = Histogram(
    'rag_processing_duration_seconds',
    'RAG processing time distribution',
    ['operation', 'cache_hit', 'model'],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0, 10.0, 30.0]
)

rag_embedding_duration = Histogram(
    'rag_embedding_duration_seconds',
    'Embedding generation time',
    ['model', 'batch_size'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

rag_generation_duration = Histogram(
    'rag_generation_duration_seconds',
    'LLM generation time',
    ['model', 'token_count_bucket'],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]
)

rag_similarity_search_duration = Histogram(
    'rag_similarity_search_duration_seconds',
    'Similarity search time',
    ['index_size_bucket'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================================================
# MÉTRIQUES DE QUALITÉ
# ============================================================================

rag_similarity_scores = Histogram(
    'rag_similarity_scores',
    'Document similarity scores distribution',
    ['query_type'],
    buckets=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)

rag_confidence_scores = Histogram(
    'rag_confidence_scores',
    'RAG response confidence scores',
    ['endpoint'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

rag_context_relevance = Histogram(
    'rag_context_relevance',
    'Relevance score of retrieved context',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# ============================================================================
# MÉTRIQUES DE CACHE
# ============================================================================

rag_cache_hit_ratio = Gauge(
    'rag_cache_hit_ratio',
    'Cache hit ratio percentage (0-1)'
)

rag_cache_operations = Counter(
    'rag_cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/error
)

rag_cache_size_bytes = Gauge(
    'rag_cache_size_bytes',
    'Total cache size in bytes',
    ['cache_type']
)

rag_cache_evictions = Counter(
    'rag_cache_evictions_total',
    'Total cache evictions',
    ['reason']  # reason: ttl_expired/size_limit/manual
)

# ============================================================================
# MÉTRIQUES D'INDEX VECTORIEL
# ============================================================================

rag_documents_indexed = Gauge(
    'rag_documents_indexed_total',
    'Total documents in RAG index',
    ['collection']
)

rag_embeddings_generated = Counter(
    'rag_embeddings_generated_total',
    'Total embeddings generated',
    ['model', 'operation']  # operation: index/query
)

rag_index_size_bytes = Gauge(
    'rag_index_size_bytes',
    'Size of the vector index in bytes',
    ['index_type']
)

rag_index_operations = Counter(
    'rag_index_operations_total',
    'Vector index operations',
    ['operation', 'status']  # operation: add/search/update/delete
)

# ============================================================================
# MÉTRIQUES DE MODÈLES IA
# ============================================================================

rag_model_requests = Counter(
    'rag_model_requests_total',
    'Total model inference requests',
    ['model_name', 'model_type', 'status']  # model_type: embedding/generation
)

rag_model_tokens = Counter(
    'rag_model_tokens_total',
    'Total tokens processed',
    ['model_name', 'token_type']  # token_type: input/output
)

rag_model_errors = Counter(
    'rag_model_errors_total',
    'Total model errors',
    ['model_name', 'error_type']
)

rag_model_fallbacks = Counter(
    'rag_model_fallbacks_total',
    'Model fallback occurrences',
    ['from_model', 'to_model', 'reason']
)

# ============================================================================
# MÉTRIQUES DE SOURCES EXTERNES
# ============================================================================

external_service_requests = Counter(
    'external_service_requests_total',
    'External service requests',
    ['service', 'endpoint', 'status']
)

external_service_latency = Histogram(
    'external_service_latency_seconds',
    'External service latency',
    ['service', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

external_service_errors = Counter(
    'external_service_errors_total',
    'External service errors',
    ['service', 'error_type']
)

# ============================================================================
# MÉTRIQUES DE RECOMMANDATIONS
# ============================================================================

recommendations_generated = Counter(
    'recommendations_generated_total',
    'Total recommendations generated',
    ['category', 'priority', 'source']
)

recommendations_quality_score = Histogram(
    'recommendations_quality_score',
    'Quality score of generated recommendations',
    ['category'],
    buckets=[0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
)

recommendations_applied = Counter(
    'recommendations_applied_total',
    'Recommendations that were applied by users',
    ['category', 'priority']
)

recommendations_effectiveness = Histogram(
    'recommendations_effectiveness_score',
    'Effectiveness score of applied recommendations',
    ['category'],
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# ============================================================================
# MÉTRIQUES SYSTÈME
# ============================================================================

rag_system_info = Info(
    'rag_system_info',
    'RAG system information'
)

rag_memory_usage_bytes = Gauge(
    'rag_memory_usage_bytes',
    'Memory usage of RAG components',
    ['component']
)

rag_active_connections = Gauge(
    'rag_active_connections',
    'Active connections to external services',
    ['service']
)

# ============================================================================
# DÉCORATEURS POUR INSTRUMENTATION AUTOMATIQUE
# ============================================================================

def track_rag_operation(operation: str, model: str = "unknown"):
    """Décorateur pour tracker automatiquement les opérations RAG"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Incrémenter les requêtes en cours
            rag_requests_in_progress.labels(endpoint=operation).inc()
            
            start_time = time.time()
            cache_hit = kwargs.get('use_cache', True) and kwargs.get('_cache_hit', False)
            
            try:
                result = await func(*args, **kwargs)
                
                # Mesurer la durée
                duration = time.time() - start_time
                rag_processing_duration.labels(
                    operation=operation,
                    cache_hit='hit' if cache_hit else 'miss',
                    model=model
                ).observe(duration)
                
                # Incrémenter le compteur de succès
                rag_requests_total.labels(
                    endpoint=operation,
                    cache_status='hit' if cache_hit else 'miss',
                    status='success',
                    model=model
                ).inc()
                
                return result
                
            except Exception as e:
                # Incrémenter le compteur d'erreurs
                duration = time.time() - start_time
                rag_processing_duration.labels(
                    operation=operation,
                    cache_hit='error',
                    model=model
                ).observe(duration)
                
                rag_requests_total.labels(
                    endpoint=operation,
                    cache_status='error',
                    status='error',
                    model=model
                ).inc()
                
                logger.error(f"RAG operation {operation} failed: {str(e)}")
                raise
                
            finally:
                # Décrémenter les requêtes en cours
                rag_requests_in_progress.labels(endpoint=operation).dec()
        
        return wrapper
    return decorator


def track_external_service(service: str, endpoint: str):
    """Décorateur pour tracker les appels aux services externes"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Mesurer la latence
                latency = time.time() - start_time
                external_service_latency.labels(
                    service=service,
                    endpoint=endpoint
                ).observe(latency)
                
                # Incrémenter le compteur de succès
                external_service_requests.labels(
                    service=service,
                    endpoint=endpoint,
                    status='success'
                ).inc()
                
                return result
                
            except Exception as e:
                # Incrémenter le compteur d'erreurs
                latency = time.time() - start_time
                external_service_latency.labels(
                    service=service,
                    endpoint=endpoint
                ).observe(latency)
                
                external_service_requests.labels(
                    service=service,
                    endpoint=endpoint,
                    status='error'
                ).inc()
                
                external_service_errors.labels(
                    service=service,
                    error_type=type(e).__name__
                ).inc()
                
                raise
        
        return wrapper
    return decorator


# ============================================================================
# FONCTIONS UTILITAIRES POUR MÉTRIQUES
# ============================================================================

def update_cache_hit_ratio(hits: int, total: int):
    """Met à jour le ratio de cache hits"""
    if total > 0:
        ratio = hits / total
        rag_cache_hit_ratio.set(ratio)


def record_similarity_scores(scores: list, query_type: str = "general"):
    """Enregistre les scores de similarité"""
    for score in scores:
        rag_similarity_scores.labels(query_type=query_type).observe(score)


def record_confidence_score(score: float, endpoint: str):
    """Enregistre le score de confiance d'une réponse"""
    rag_confidence_scores.labels(endpoint=endpoint).observe(score)


def update_documents_count(count: int, collection: str = "default"):
    """Met à jour le nombre de documents indexés"""
    rag_documents_indexed.labels(collection=collection).set(count)


def record_model_tokens(model_name: str, input_tokens: int, output_tokens: int):
    """Enregistre le nombre de tokens traités"""
    rag_model_tokens.labels(
        model_name=model_name,
        token_type='input'
    ).inc(input_tokens)
    
    rag_model_tokens.labels(
        model_name=model_name,
        token_type='output'
    ).inc(output_tokens)


def record_recommendation_generated(category: str, priority: str, source: str, quality_score: float = None):
    """Enregistre une recommandation générée"""
    recommendations_generated.labels(
        category=category,
        priority=priority,
        source=source
    ).inc()
    
    if quality_score is not None:
        recommendations_quality_score.labels(category=category).observe(quality_score)


def initialize_rag_metrics():
    """Initialise les métriques au démarrage"""
    try:
        # Définir les informations système
        rag_system_info.info({
            'version': '2.0.0',
            'embedding_model': 'nomic-embed-text',
            'generation_model': 'llama3:8b-instruct',
            'index_type': 'faiss',
            'cache_backend': 'redis'
        })
        
        logger.info("RAG metrics initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG metrics: {str(e)}")


# Initialiser les métriques au chargement du module
initialize_rag_metrics()

