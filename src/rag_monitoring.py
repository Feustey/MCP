import logging
from datetime import datetime
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

class RAGMonitoring:
    def __init__(self):
        # Métriques Prometheus
        self.query_counter = Counter('rag_queries_total', 'Total des requêtes RAG')
        self.cache_hits = Counter('rag_cache_hits', 'Nombre de hits du cache')
        self.processing_time = Histogram('rag_processing_seconds', 'Temps de traitement RAG')
        self.embedding_cache_size = Gauge('rag_embedding_cache_size', 'Taille du cache d\'embeddings')
        
        # Configuration du logging
        self.logger = logging.getLogger("rag_monitoring")
        self.logger.setLevel(logging.INFO)
        
        # Configuration du handler de fichier
        handler = logging.FileHandler('logs/rag_monitoring.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        
    async def log_query(self, query: str, context: Dict[str, Any], duration: float):
        """Enregistre les métriques d'une requête"""
        self.query_counter.inc()
        self.processing_time.observe(duration)
        
        self.logger.info(
            f"RAG Query - Duration: {duration:.2f}s, "
            f"Context Size: {len(str(context))} bytes"
        )
        
    async def log_cache_hit(self, cache_type: str):
        """Enregistre un hit du cache"""
        self.cache_hits.inc()
        self.logger.info(f"Cache hit - Type: {cache_type}")
        
    async def update_embedding_cache_size(self, size: int):
        """Met à jour la taille du cache d'embeddings"""
        self.embedding_cache_size.set(size)
        
    async def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Enregistre une erreur"""
        self.logger.error(
            f"RAG Error: {str(error)}, Context: {context if context else 'None'}"
        ) 