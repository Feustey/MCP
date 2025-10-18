"""
Système RAG optimisé pour MCP avec async/await et performance améliorée
Inclut cache distribué, rate limiting et monitoring intégré

Dernière mise à jour: 9 janvier 2025
"""

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import hashlib
import numpy as np
from pathlib import Path

import aiofiles
import redis.asyncio as aioredis
from anthropic import AsyncAnthropic
# from anthropic.types import Message  # Not available in anthropic 0.9.0
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer
import tiktoken
from openai import AsyncOpenAI
from openai._exceptions import OpenAIError
import aiohttp

from config import settings
from src.logging_config import get_logger, log_performance
from src.performance_metrics import PerformanceTracker
from src.exceptions import RAGError, EmbeddingError, CacheError

logger = get_logger(__name__)
performance_tracker = PerformanceTracker("rag_system", enabled=getattr(settings, "perf_enable_metrics", True))


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


class RedisEmbeddingCache:
    """Cache distribué pour les embeddings avec TTL intelligent"""
    
    def __init__(self, redis_client: aioredis.Redis, default_ttl: int):
        self.redis = redis_client
        self.prefix = "embeddings"
        self.default_ttl = default_ttl
    
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


class InMemoryEmbeddingCache:
    """Cache en mémoire pour les embeddings (fallback lorsque Redis indisponible)"""

    def __init__(self, default_ttl: int):
        self.default_ttl = default_ttl
        self._store: Dict[str, Tuple[EmbeddingResult, datetime]] = {}
        self._lock = asyncio.Lock()

    def _get_cache_key(self, text: str, model: str) -> str:
        return hashlib.sha256(f"{model}:{text}".encode()).hexdigest()

    async def get(self, text: str, model: str) -> Optional[EmbeddingResult]:
        async with self._lock:
            cache_key = self._get_cache_key(text, model)
            result = self._store.get(cache_key)
            if not result:
                return None
            embedding, expires_at = result
            if expires_at < datetime.utcnow():
                self._store.pop(cache_key, None)
                return None
            cached_copy = EmbeddingResult(
                embedding=embedding.embedding,
                model=embedding.model,
                token_count=embedding.token_count,
                duration_ms=embedding.duration_ms,
                cached=True
            )
            return cached_copy

    async def set(self, text: str, result: EmbeddingResult, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            cache_key = self._get_cache_key(text, result.model)
            expires_at = datetime.utcnow() + timedelta(seconds=ttl or self.default_ttl)
            self._store[cache_key] = (result, expires_at)
        return True

    async def size(self) -> int:
        async with self._lock:
            return len(self._store)


class AsyncEmbeddingProvider:
    """Provider d'embeddings asynchrone avec fallback intelligent"""

    def __init__(self):
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.openai_client: Optional[AsyncOpenAI] = None
        if settings.ai_openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.ai_openai_api_key)
        self.openai_embedding_model = settings.ai_openai_embedding_model or settings.ai_default_embedding_model
        self.local_model: Optional[SentenceTransformer] = None
        self._local_model_lock = asyncio.Lock()
        self._embedding_dimension = settings.qdrant_vector_size
        # Ollama
        from config.rag_config import settings as rag_settings
        from src.clients.ollama_client import ollama_client
        self._rag_settings = rag_settings
        self._ollama = ollama_client

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    async def _get_local_model(self) -> SentenceTransformer:
        if self.local_model is None:
            async with self._local_model_lock:
                if self.local_model is None:
                    try:
                        self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
                        logger.info("Modèle local d'embedding chargé (fallback)")
                    except Exception as e:
                        logger.error("Erreur chargement modèle local", error=str(e))
                        raise
        return self.local_model

    async def _embedding_via_openai(self, text: str) -> EmbeddingResult:
        if not self.openai_client:
            raise EmbeddingError("Client OpenAI non configuré")

        start_time = time.time()
        token_count = len(self.tokenizer.encode(text))

        try:
            response = await self.openai_client.embeddings.create(
                model=self.openai_embedding_model,
                input=text
            )
            vector = response.data[0].embedding
            duration_ms = (time.time() - start_time) * 1000
            self._embedding_dimension = len(vector)
            log_performance("openai_embedding", duration_ms, token_count=token_count)
            return EmbeddingResult(
                embedding=vector,
                model=self.openai_embedding_model,
                token_count=token_count,
                duration_ms=duration_ms
            )
        except OpenAIError as e:
            logger.error("Erreur embedding OpenAI", error=str(e), text_length=len(text))
            raise EmbeddingError(str(e))
        except Exception as e:
            logger.error("Erreur inattendue embedding OpenAI", error=str(e))
            raise EmbeddingError(str(e))

    async def _embedding_via_local(self, text: str) -> EmbeddingResult:
        start_time = time.time()
        model = await self._get_local_model()
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(None, model.encode, text)
        vector_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        duration_ms = (time.time() - start_time) * 1000
        self._embedding_dimension = len(vector_list)
        log_performance("local_embedding", duration_ms)
        return EmbeddingResult(
            embedding=vector_list,
            model="all-MiniLM-L6-v2",
            token_count=len(self.tokenizer.encode(text)),
            duration_ms=duration_ms
        )

    async def get_embedding(self, text: str) -> EmbeddingResult:
        # Priorité: Ollama embeddings si configuré
        try:
            start_time = time.time()
            vector = await self._ollama.embed(text, self._rag_settings.EMBED_MODEL)
            duration_ms = (time.time() - start_time) * 1000
            self._embedding_dimension = len(vector)
            log_performance("ollama_embedding", duration_ms, token_count=len(self.tokenizer.encode(text)))
            return EmbeddingResult(
                embedding=vector,
                model=self._rag_settings.EMBED_MODEL,
                token_count=len(self.tokenizer.encode(text)),
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error("Erreur embedding Ollama, tentative OpenAI/local", error=str(e))
            try:
                return await self._embedding_via_openai(text)
            except EmbeddingError:
                logger.warning("Fallback embedding local", text_length=len(text))
                return await self._embedding_via_local(text)


class AsyncLLMResponder:
    """Génère des réponses en s'appuyant sur les chunks sélectionnés"""

    def __init__(self):
        self.temperature = 0.2
        self.max_tokens = getattr(settings, "ai_max_output_tokens", 600)

        self.anthropic_client: Optional[AsyncAnthropic] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        # Ollama
        from config.rag_config import settings as rag_settings
        from src.clients.ollama_client import ollama_client
        self._rag_settings = rag_settings
        self._ollama = ollama_client

        if settings.ai_anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ai_anthropic_api_key, timeout=45.0)

        if settings.ai_openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.ai_openai_api_key)

        self.anthropic_model = settings.ai_default_model if settings.ai_default_model.lower().startswith("claude") else "claude-3-haiku-20240307"
        self.openai_model = settings.ai_openai_model

    async def generate(self, question: str, sources: List[Tuple[DocumentChunk, float]]) -> str:
        context_sections = []
        for idx, (chunk, score) in enumerate(sources, start=1):
            context_sections.append(
                f"[Source {idx} | fichier: {chunk.source_file or 'inconnu'} | score={score:.3f}]\n{chunk.content.strip()}"
            )
        context = "\n\n".join(context_sections) if context_sections else "Aucun contexte disponible."

        system_instructions = (
            "Tu es un assistant expert du Lightning Network. Réponds en français,"
            " en synthétisant uniquement les informations présentes dans le contexte."
            " Signale explicitement si le contexte ne permet pas de répondre."
        )
        user_prompt = f"Contexte:\n{context}\n\nQuestion:\n{question.strip()}"

        # Priorité au runtime RAG: Ollama
        try:
            prompt = (
                "Tu es un assistant expert du Lightning Network. Réponds en français,"
                " en synthétisant uniquement les informations présentes dans le contexte."
                " Signale explicitement si le contexte ne permet pas de répondre.\n\n"
                f"Contexte:\n{context}\n\nQuestion:\n{question.strip()}"
            )
            text = await self._ollama.generate(
                prompt=prompt,
                model=self._rag_settings.GEN_MODEL,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                num_ctx=8192,
            )
            return text.strip()
        except Exception as e:
            logger.error("Ollama failure, fallback Anthropic/OpenAI", error=str(e))

        # Priorité à Anthropic si disponible et modèle compatible
        if self.anthropic_client and self.anthropic_model.lower().startswith("claude"):
            try:
                response = await self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_instructions,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                text = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                return text.strip()
            except Exception as e:
                logger.error("Anthropic failure, fallback OpenAI", error=str(e))

        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return (response.choices[0].message.content or "").strip()
            except OpenAIError as e:
                logger.error("OpenAI failure during generation", error=str(e))
            except Exception as e:
                logger.error("Erreur inattendue lors de la génération OpenAI", error=str(e))

        raise RAGError("Aucun fournisseur LLM disponible pour générer la réponse")


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
        """Divise un document en chunks en essayant de respecter les frontières de phrases"""
        tokens = self.tokenizer.encode(document)
        total_tokens = len(tokens)
        if total_tokens == 0:
            return []

        chunks: List[DocumentChunk] = []
        start_idx = 0
        chunk_idx = 0

        while start_idx < total_tokens:
            end_idx = min(start_idx + self.max_chunk_size, total_tokens)
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = self.tokenizer.decode(chunk_tokens).strip()

            if not chunk_text:
                start_idx = end_idx
                continue

            if end_idx < total_tokens:
                last_punctuation = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('! '),
                    chunk_text.rfind('? ')
                )
                if last_punctuation != -1 and last_punctuation > len(chunk_text) * 0.4:
                    trimmed_text = chunk_text[: last_punctuation + 1].strip()
                    trimmed_tokens = self.tokenizer.encode(trimmed_text)
                    if len(trimmed_tokens) > self.chunk_overlap:
                        chunk_text = trimmed_text
                        chunk_tokens = trimmed_tokens
                        end_idx = start_idx + len(chunk_tokens)

            chunk = DocumentChunk(
                content=chunk_text,
                token_count=len(chunk_tokens),
                source_file=filename,
                metadata={
                    "chunk_index": chunk_idx,
                    "start_token": start_idx,
                    "end_token": end_idx,
                    "total_tokens": total_tokens
                }
            )
            chunks.append(chunk)
            chunk_idx += 1

            if end_idx >= total_tokens:
                break

            if self.chunk_overlap > 0:
                start_idx = max(end_idx - self.chunk_overlap, 0)
            else:
                start_idx = end_idx

            if start_idx <= chunk.metadata["start_token"]:
                # Safety to avoid infinite loop if overlap misconfigured
                start_idx = chunk.metadata["end_token"]

        return chunks


class OptimizedRAGWorkflow:
    """Workflow RAG optimisé avec async et performance améliorée"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.embedding_cache: Optional[Union[RedisEmbeddingCache, InMemoryEmbeddingCache]] = None
        self.embedding_provider = AsyncEmbeddingProvider()
        self.embedding_cache_ttl = getattr(settings, "perf_embedding_cache_ttl", 86400)
        self.responder = AsyncLLMResponder()
        self.document_processor = DocumentProcessor()
        self.chunks: List[DocumentChunk] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self.qdrant_client: Optional[AsyncQdrantClient] = None
        self.qdrant_collection = settings.qdrant_collection
        self.qdrant_distance = settings.qdrant_distance.lower()
        self._qdrant_collection_ready = False
        self._initialized = False
    
    async def initialize(self):
        """Initialise les connexions asynchrones"""
        if self._initialized:
            return
        
        try:
            await self._init_embedding_cache()
            await self._init_qdrant()
            self._initialized = True
            logger.info(
                "RAG workflow initialisé",
                cache_type="redis" if isinstance(self.embedding_cache, RedisEmbeddingCache) else "memory",
                qdrant_enabled=bool(self.qdrant_client)
            )
            
        except Exception as e:
            logger.error("Erreur initialisation RAG", error=str(e))
            raise RAGError(f"Échec initialisation: {e}")

    async def close(self):
        """Ferme les connexions"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        if self.qdrant_client:
            await self.qdrant_client.close()
            self.qdrant_client = None
        self.embedding_cache = None
        self._initialized = False

    async def _init_embedding_cache(self):
        """Initialise le cache d'embeddings en privilégiant Redis"""
        try:
            redis_url = settings.get_redis_url()
        except Exception:
            redis_url = None

        if redis_url:
            try:
                self.redis_client = aioredis.from_url(redis_url)
                await self.redis_client.ping()
                self.embedding_cache = RedisEmbeddingCache(self.redis_client, self.embedding_cache_ttl)
                logger.info("Cache Redis initialisé pour les embeddings", redis_url=redis_url)
                return
            except Exception as e:
                logger.warning("Redis indisponible pour les embeddings, fallback mémoire", error=str(e))
                if self.redis_client:
                    await self.redis_client.close()
                self.redis_client = None

        self.embedding_cache = InMemoryEmbeddingCache(self.embedding_cache_ttl)
        logger.info("Cache d'embeddings en mémoire activé")

    async def _init_qdrant(self):
        """Initialise la connexion à Qdrant si disponible"""
        if not settings.qdrant_url:
            logger.info("Qdrant non configuré - utilisation du fallback mémoire")
            return

        try:
            self.qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=5.0
            )
            await self._ensure_qdrant_collection(self.embedding_provider.embedding_dimension)
            self._qdrant_collection_ready = True
            logger.info("Connexion Qdrant établie", collection=self.qdrant_collection)
        except Exception as e:
            logger.warning("Impossible d'initialiser Qdrant", error=str(e))
            if self.qdrant_client:
                await self.qdrant_client.close()
            self.qdrant_client = None
            self._qdrant_collection_ready = False

    async def _ensure_qdrant_collection(self, vector_size: int):
        if not self.qdrant_client:
            return
        if self._qdrant_collection_ready:
            return
        try:
            await self.qdrant_client.get_collection(self.qdrant_collection)
            self._qdrant_collection_ready = True
            return
        except Exception:
            pass

        distance = {
            "cosine": qmodels.Distance.COSINE,
            "dot": qmodels.Distance.DOT,
            "innerproduct": qmodels.Distance.DOT,
            "euclid": qmodels.Distance.EUCLID,
            "l2": qmodels.Distance.EUCLID
        }.get(self.qdrant_distance, qmodels.Distance.COSINE)

        await self.qdrant_client.create_collection(
            collection_name=self.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=distance
            )
        )
        self._qdrant_collection_ready = True

    async def _upsert_chunks_to_qdrant(self, chunks: List[DocumentChunk]):
        if not self.qdrant_client:
            return

        ids: List[str] = []
        vectors: List[List[float]] = []
        payloads: List[Dict[str, Any]] = []

        for chunk in chunks:
            if not chunk.embedding:
                continue
            payloads.append({
                "content": chunk.content,
                "source": chunk.source_file,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
                "created_at": (chunk.created_at or datetime.utcnow()).isoformat(),
                "chunk_id": chunk.chunk_id
            })
            vectors.append(chunk.embedding)
            ids.append(chunk.chunk_id or uuid.uuid4().hex)

        if not ids:
            return

        await self._ensure_qdrant_collection(self.embedding_provider.embedding_dimension)
        await self.qdrant_client.upsert(
            collection_name=self.qdrant_collection,
            points=qmodels.Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads
            )
        )

    def _convert_distance_to_similarity(self, distance: float) -> float:
        metric = self.qdrant_distance
        if metric in {"cosine", "cos"}:
            return max(0.0, 1.0 - distance)
        if metric in {"dot", "innerproduct"}:
            return distance
        return 1.0 / (1.0 + distance)

    def _find_similar_chunks_local(self, query_embedding: np.ndarray, top_k: int) -> List[Tuple[DocumentChunk, float]]:
        if self.embeddings_matrix is None or len(self.chunks) == 0:
            return []

        similarities = np.dot(self.embeddings_matrix, query_embedding)
        similarities = similarities / (
            np.linalg.norm(self.embeddings_matrix, axis=1) * np.linalg.norm(query_embedding)
        )

        top_indices = np.argsort(similarities)[-top_k:][::-1]
        results: List[Tuple[DocumentChunk, float]] = []
        for idx in top_indices:
            if idx < len(self.chunks) and self.chunks[idx].embedding:
                results.append((self.chunks[idx], float(similarities[idx])))
        return results
    
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

        # Persistance dans Qdrant si disponible
        await self._upsert_chunks_to_qdrant(chunks)
    
    async def _get_chunk_embedding(self, chunk: DocumentChunk):
        """Obtient l'embedding d'un chunk avec cache"""
        try:
            cached_result: Optional[EmbeddingResult] = None
            if self.embedding_cache:
                candidate_models = []
                if self.embedding_provider.openai_client:
                    candidate_models.append(self.embedding_provider.openai_embedding_model)
                candidate_models.append("all-MiniLM-L6-v2")
                for model_name in candidate_models:
                    if not model_name:
                        continue
                    cached_result = await self.embedding_cache.get(chunk.content, model_name)
                    if cached_result:
                        break

            if cached_result:
                chunk.embedding = cached_result.embedding
                logger.debug("Embedding récupéré du cache", chunk_id=chunk.chunk_id)
                return

            # Génère l'embedding
            result = await self.embedding_provider.get_embedding(chunk.content)
            chunk.embedding = result.embedding
            await self._ensure_qdrant_collection(len(result.embedding))
            
            # Met en cache
            if self.embedding_cache:
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
            if not similar_chunks:
                raise RAGError("Aucun contexte pertinent trouvé pour cette requête")

            answer = await self.responder.generate(query_text, similar_chunks)
            
            duration_ms = (time.time() - start_time) * 1000
            confidence_values = [score for _, score in similar_chunks]
            confidence_score = float(np.mean(confidence_values)) if confidence_values else 0.0
            context_tokens = sum(chunk.token_count for chunk, _ in similar_chunks)
            
            result = QueryResult(
                answer=answer,
                sources=[chunk for chunk, _ in similar_chunks],
                confidence_score=confidence_score,
                processing_time_ms=duration_ms,
                token_usage={
                    "query_tokens": query_embedding_result.token_count,
                    "context_tokens": context_tokens
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
        """Recherche les chunks les plus pertinents en privilégiant Qdrant"""
        if self.qdrant_client and self._qdrant_collection_ready:
            try:
                search_results = await self.qdrant_client.search(
                    collection_name=self.qdrant_collection,
                    query_vector=query_embedding.tolist(),
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False
                )
                matched_chunks: List[Tuple[DocumentChunk, float]] = []
                for point in search_results:
                    payload = point.payload or {}
                    chunk = DocumentChunk(
                        content=payload.get("content", ""),
                        token_count=int(payload.get("token_count", 0)),
                        metadata=payload.get("metadata", {}),
                        source_file=payload.get("source", ""),
                        chunk_id=payload.get("chunk_id") or str(point.id),
                        created_at=datetime.fromisoformat(payload["created_at"]) if payload.get("created_at") else None
                    )
                    similarity = self._convert_distance_to_similarity(float(point.score))
                    matched_chunks.append((chunk, similarity))
                if matched_chunks:
                    return matched_chunks
            except Exception as e:
                logger.error("Erreur recherche Qdrant", error=str(e))

        # Fallback sur la recherche en mémoire si Qdrant indisponible ou vide
        return self._find_similar_chunks_local(query_embedding, top_k)


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
