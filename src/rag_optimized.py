"""
Système RAG optimisé pour MCP avec async/await et performance améliorée
Inclut cache distribué, rate limiting et monitoring intégré

Dernière mise à jour: 9 janvier 2025
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import hashlib
import numpy as np
from pathlib import Path

import aiofiles
import redis.asyncio as aioredis
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer
import tiktoken

from config import settings
from src.logging_config import get_logger, log_performance
from src.performance_metrics import PerformanceTracker
from src.circuit_breaker import CircuitBreakerRegistry
from src.exceptions import RAGError, EmbeddingError, CacheError

logger = get_logger(__name__)
performance_tracker = PerformanceTracker("rag_system")


@dataclass
class EmbeddingResult:
    """Résultat d'embedding avec métadonnées"""
    embedding: List[float]
    model: str
    token_count: int
    duration_ms: float
    cached: bool = False


@dataclass
class DocumentChunk:
    """Chunk de document avec métadonnées enrichies"""
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    chunk_id: str = ""
    source_file: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.chunk_id:
            # Génère un ID unique basé sur le contenu
            content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
            self.chunk_id = f"{self.source_file}_{content_hash}"
        
        if not self.created_at:
            self.created_at = datetime.utcnow()


@dataclass
class QueryResult:
    """Résultat de requête RAG avec métriques"""
    answer: str
    sources: List[DocumentChunk]
    confidence_score: float
    processing_time_ms: float
    cache_hit: bool = False
    token_usage: Dict[str, int] = field(default_factory=dict)


class EmbeddingCache:
    """Cache distribué pour les embeddings avec TTL intelligent"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.prefix = "embeddings"
        self.default_ttl = settings.performance.embedding_cache_ttl
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Génère une clé de cache unique"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"{self.prefix}:{model}:{text_hash}"
    
    async def get(self, text: str, model: str) -> Optional[EmbeddingResult]:
        """Récupère un embedding du cache"""
        try:
            cache_key = self._get_cache_key(text, model)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return EmbeddingResult(
                    embedding=data["embedding"],
                    model=data["model"],
                    token_count=data["token_count"],
                    duration_ms=data["duration_ms"],
                    cached=True
                )
            return None
            
        except Exception as e:
            logger.warning("Erreur lecture cache embedding", error=str(e))
            return None
    
    async def set(self, text: str, result: EmbeddingResult, ttl: Optional[int] = None) -> bool:
        """Stocke un embedding dans le cache"""
        try:
            cache_key = self._get_cache_key(text, result.model)
            cache_data = {
                "embedding": result.embedding,
                "model": result.model,
                "token_count": result.token_count,
                "duration_ms": result.duration_ms,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            await self.redis.setex(
                cache_key,
                ttl or self.default_ttl,
                json.dumps(cache_data)
            )
            return True
            
        except Exception as e:
            logger.error("Erreur écriture cache embedding", error=str(e))
            return False


class AsyncEmbeddingProvider:
    """Provider d'embeddings asynchrone avec fallback et rate limiting"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=settings.ai_openai_api_key,
            timeout=30.0,
            max_retries=3
        )
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.circuit_breaker = CircuitBreakerRegistry.get("openai_embeddings")
        
        # Modèle local en fallback
        self.local_model = None
        self._local_model_lock = asyncio.Lock()
    
    async def _get_local_model(self) -> SentenceTransformer:
        """Charge le modèle local en lazy loading"""
        if self.local_model is None:
            async with self._local_model_lock:
                if self.local_model is None:
                    try:
                        # Utilise un modèle plus léger en fallback
                        self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
                        logger.info("Modèle local d'embedding chargé")
                    except Exception as e:
                        logger.error("Erreur chargement modèle local", error=str(e))
                        raise
        return self.local_model
    
    async def get_embedding_openai(self, text: str) -> EmbeddingResult:
        """Obtient un embedding via OpenAI"""
        start_time = time.time()
        
        try:
            # Compte les tokens
            tokens = self.tokenizer.encode(text)
            token_count = len(tokens)
            
            # Appel via circuit breaker
            response = await self.circuit_breaker.execute(
                self.openai_client.embeddings.create,
                model=settings.ai_openai_embedding_model,
                input=text
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = EmbeddingResult(
                embedding=response.data[0].embedding,
                model=settings.ai_openai_embedding_model,
                token_count=token_count,
                duration_ms=duration_ms
            )
            
            # Log des métriques
            log_performance("openai_embedding", duration_ms, token_count=token_count)
            
            return result
            
        except Exception as e:
            logger.error("Erreur embedding OpenAI", error=str(e), text_length=len(text))
            raise EmbeddingError(f"Échec embedding OpenAI: {e}")
    
    async def get_embedding_local(self, text: str) -> EmbeddingResult:
        """Obtient un embedding via le modèle local"""
        start_time = time.time()
        
        try:
            model = await self._get_local_model()
            
            # Exécute dans un thread pour éviter le blocage
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, model.encode, text
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = EmbeddingResult(
                embedding=embedding.tolist(),
                model="all-MiniLM-L6-v2",
                token_count=len(text.split()),  # Approximation
                duration_ms=duration_ms
            )
            
            log_performance("local_embedding", duration_ms)
            
            return result
            
        except Exception as e:
            logger.error("Erreur embedding local", error=str(e))
            raise EmbeddingError(f"Échec embedding local: {e}")
    
    async def get_embedding(self, text: str, prefer_local: bool = False) -> EmbeddingResult:
        """Obtient un embedding avec fallback automatique"""
        
        if prefer_local or settings.is_development:
            try:
                return await self.get_embedding_local(text)
            except Exception:
                logger.warning("Fallback vers OpenAI après échec local")
                return await self.get_embedding_openai(text)
        else:
            try:
                return await self.get_embedding_openai(text)
            except Exception:
                logger.warning("Fallback vers modèle local après échec OpenAI")
                return await self.get_embedding_local(text)


class DocumentProcessor:
    """Processeur de documents avec chunking intelligent"""
    
    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_chunk_size = 512  # tokens
        self.chunk_overlap = 50    # tokens
    
    async def load_documents_async(self, directory: Union[str, Path]) -> List[str]:
        """Charge les documents de manière asynchrone"""
        directory = Path(directory)
        if not directory.exists():
            raise RAGError(f"Répertoire inexistant: {directory}")
        
        documents = []
        tasks = []
        
        for txt_file in directory.glob("*.txt"):
            tasks.append(self._load_file_async(txt_file))
        
        if not tasks:
            logger.warning("Aucun fichier .txt trouvé", directory=str(directory))
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Erreur chargement fichier", 
                           file=str(list(directory.glob("*.txt"))[i]),
                           error=str(result))
            else:
                documents.append(result)
        
        logger.info("Documents chargés", count=len(documents))
        return documents
    
    async def _load_file_async(self, filepath: Path) -> str:
        """Charge un fichier de manière asynchrone"""
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
                return content
        except Exception as e:
            logger.error("Erreur lecture fichier", file=str(filepath), error=str(e))
            raise
    
    def create_chunks(self, documents: List[str], filenames: List[str] = None) -> List[DocumentChunk]:
        """Crée des chunks intelligents à partir des documents"""
        if filenames is None:
            filenames = [f"doc_{i}" for i in range(len(documents))]
        
        chunks = []
        
        for doc_idx, (document, filename) in enumerate(zip(documents, filenames)):
            doc_chunks = self._chunk_document(document, filename)
            chunks.extend(doc_chunks)
        
        logger.info("Chunks créés", 
                   total_chunks=len(chunks),
                   avg_tokens=np.mean([c.token_count for c in chunks]))
        
        return chunks
    
    def _chunk_document(self, document: str, filename: str) -> List[DocumentChunk]:
        """Divise un document en chunks avec overlap"""
        tokens = self.tokenizer.encode(document)
        chunks = []
        
        start_idx = 0
        chunk_idx = 0
        
        while start_idx < len(tokens):
            end_idx = min(start_idx + self.max_chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Reconvertit en texte
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunk = DocumentChunk(
                content=chunk_text,
                token_count=len(chunk_tokens),
                source_file=filename,
                metadata={
                    "chunk_index": chunk_idx,
                    "start_token": start_idx,
                    "end_token": end_idx,
                    "total_tokens": len(tokens)
                }
            )
            
            chunks.append(chunk)
            
            # Avance avec overlap
            start_idx += self.max_chunk_size - self.chunk_overlap
            chunk_idx += 1
        
        return chunks


class OptimizedRAGWorkflow:
    """Workflow RAG optimisé avec async et performance améliorée"""
    
    def __init__(self):
        self.redis_client = None
        self.embedding_cache = None
        self.embedding_provider = AsyncEmbeddingProvider()
        self.document_processor = DocumentProcessor()
        self.chunks: List[DocumentChunk] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialise les connexions asynchrones"""
        if self._initialized:
            return
        
        try:
            # Connexion Redis
            self.redis_client = aioredis.from_url(
                settings.get_redis_url(),
                max_connections=settings.redis.max_connections,
                retry_on_timeout=settings.redis.retry_on_timeout,
                socket_timeout=settings.redis.socket_timeout,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                health_check_interval=settings.redis.health_check_interval
            )
            
            # Test de connexion
            await self.redis_client.ping()
            
            # Initialise le cache
            self.embedding_cache = EmbeddingCache(self.redis_client)
            
            self._initialized = True
            logger.info("RAG workflow initialisé")
            
        except Exception as e:
            logger.error("Erreur initialisation RAG", error=str(e))
            raise RAGError(f"Échec initialisation: {e}")
    
    async def close(self):
        """Ferme les connexions"""
        if self.redis_client:
            await self.redis_client.close()
        self._initialized = False
    
    @asynccontextmanager
    async def lifespan(self):
        """Gestionnaire de contexte pour la durée de vie"""
        await self.initialize()
        try:
            yield self
        finally:
            await self.close()
    
    async def ingest_documents(self, directory: Union[str, Path]) -> bool:
        """Ingère des documents avec processing parallèle"""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Charge les documents
            documents = await self.document_processor.load_documents_async(directory)
            
            if not documents:
                logger.warning("Aucun document à ingérer")
                return False
            
            # Crée les chunks
            filenames = [f.name for f in Path(directory).glob("*.txt")]
            self.chunks = self.document_processor.create_chunks(documents, filenames)
            
            # Génère les embeddings en parallèle (par batch)
            batch_size = 10  # Limite pour éviter la surcharge
            embedding_tasks = []
            
            for i in range(0, len(self.chunks), batch_size):
                batch_chunks = self.chunks[i:i + batch_size]
                batch_task = self._process_chunk_batch(batch_chunks)
                embedding_tasks.append(batch_task)
            
            # Exécute tous les batchs
            await asyncio.gather(*embedding_tasks)
            
            # Construit la matrice d'embeddings
            embeddings = [chunk.embedding for chunk in self.chunks if chunk.embedding]
            if embeddings:
                self.embeddings_matrix = np.array(embeddings, dtype=np.float32)
            
            duration = (time.time() - start_time) * 1000
            log_performance("document_ingestion", duration,
                          documents_count=len(documents),
                          chunks_count=len(self.chunks))
            
            logger.info("Ingestion terminée",
                       documents=len(documents),
                       chunks=len(self.chunks),
                       embeddings=len(embeddings),
                       duration_ms=duration)
            
            return True
            
        except Exception as e:
            logger.error("Erreur ingestion documents", error=str(e))
            raise RAGError(f"Échec ingestion: {e}")
    
    async def _process_chunk_batch(self, chunks: List[DocumentChunk]):
        """Traite un batch de chunks pour les embeddings"""
        tasks = []
        
        for chunk in chunks:
            task = self._get_chunk_embedding(chunk)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _get_chunk_embedding(self, chunk: DocumentChunk):
        """Obtient l'embedding d'un chunk avec cache"""
        try:
            # Vérifie le cache
            cached_result = await self.embedding_cache.get(
                chunk.content, 
                settings.ai.openai_embedding_model
            )
            
            if cached_result:
                chunk.embedding = cached_result.embedding
                logger.debug("Embedding récupéré du cache", chunk_id=chunk.chunk_id)
                return
            
            # Génère l'embedding
            result = await self.embedding_provider.get_embedding(chunk.content)
            chunk.embedding = result.embedding
            
            # Met en cache
            await self.embedding_cache.set(chunk.content, result)
            
            logger.debug("Embedding généré et mis en cache", 
                        chunk_id=chunk.chunk_id,
                        duration_ms=result.duration_ms)
            
        except Exception as e:
            logger.error("Erreur embedding chunk", 
                        chunk_id=chunk.chunk_id,
                        error=str(e))
            # Ne propage pas l'erreur pour ne pas faire échouer tout le batch
    
    async def query(self, query_text: str, top_k: int = 3) -> QueryResult:
        """Exécute une requête RAG optimisée"""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Génère l'embedding de la requête
            query_embedding_result = await self.embedding_provider.get_embedding(query_text)
            query_embedding = np.array(query_embedding_result.embedding, dtype=np.float32)
            
            # Trouve les documents similaires
            similar_chunks = await self._find_similar_chunks(query_embedding, top_k)
            
            # Génère la réponse (version simplifiée pour l'exemple)
            context = "\n\n".join([chunk.content for chunk, _ in similar_chunks])
            
            # Ici, on utiliserait OpenAI pour générer la réponse
            # Pour l'exemple, on retourne une réponse simple
            answer = f"Basé sur le contexte fourni: {context[:200]}..."
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = QueryResult(
                answer=answer,
                sources=[chunk for chunk, _ in similar_chunks],
                confidence_score=np.mean([score for _, score in similar_chunks]),
                processing_time_ms=duration_ms,
                token_usage={
                    "query_tokens": query_embedding_result.token_count,
                    "context_tokens": sum(chunk.token_count for chunk, _ in similar_chunks)
                }
            )
            
            log_performance("rag_query", duration_ms,
                          query_length=len(query_text),
                          sources_count=len(similar_chunks))
            
            return result
            
        except Exception as e:
            logger.error("Erreur requête RAG", error=str(e), query=query_text[:100])
            raise RAGError(f"Échec requête: {e}")
    
    async def _find_similar_chunks(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[DocumentChunk, float]]:
        """Trouve les chunks les plus similaires"""
        if self.embeddings_matrix is None or len(self.chunks) == 0:
            return []
        
        # Calcule les similarités cosinus
        similarities = np.dot(self.embeddings_matrix, query_embedding)
        similarities = similarities / (
            np.linalg.norm(self.embeddings_matrix, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Récupère les top_k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if idx < len(self.chunks) and self.chunks[idx].embedding:
                results.append((self.chunks[idx], float(similarities[idx])))
        
        return results


# Instance globale pour réutilisation
rag_workflow = OptimizedRAGWorkflow()

# Fonctions d'interface simplifiée
async def initialize_rag():
    """Initialise le système RAG"""
    await rag_workflow.initialize()

async def ingest_documents(directory: Union[str, Path]) -> bool:
    """Ingère des documents"""
    return await rag_workflow.ingest_documents(directory)

async def query_rag(query: str, top_k: int = 3) -> QueryResult:
    """Exécute une requête RAG"""
    return await rag_workflow.query(query, top_k)

async def close_rag():
    """Ferme le système RAG"""
    await rag_workflow.close() 