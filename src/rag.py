import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from uuid import uuid4
import logging
import numpy as np
from sentence_transformers import util
from transformers import GPT2Tokenizer
from config.rag_config import settings as rag_settings
from src.clients.ollama_client import ollama_client
from src.rag_ollama_adapter import OllamaRAGAdapter
import redis.asyncio as redis
import asyncio
from src.models import Document as PydanticDocument, QueryHistory as PydanticQueryHistory, SystemStats as PydanticSystemStats
from src.mongo_operations import MongoOperations
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGWorkflow:
    def __init__(self, redis_ops: Optional[RedisOperations] = None):
        # Initialisation de l'adaptateur Ollama pour le pipeline RAG (embeddings + génération)
        self.ai_adapter = OllamaRAGAdapter(
            embed_model=rag_settings.EMBED_MODEL,
            gen_model=rag_settings.GEN_MODEL,
            dimension=rag_settings.EMBED_DIMENSION,
            num_ctx=rag_settings.GEN_NUM_CTX,
            fallback_model=rag_settings.GEN_MODEL_FALLBACK,
        )
        
        # Chargement du prompt système
        self.system_prompt = self._load_system_prompt()
        
        # Configuration du tokenizer
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        
        # Configuration de la matrice d'embeddings
        self.dimension = rag_settings.EMBED_DIMENSION
        self.embeddings_matrix = None
        self.documents = []
        
        # Configuration Redis
        self.redis_ops = redis_ops
        self.response_cache_ttl = rag_settings.CACHE_TTL_ANSWER

        # Initialisation MongoDB
        self.mongo_ops = MongoOperations()
        self._init_task = None

    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis le fichier prompt-rag.md."""
        try:
            with open('prompt-rag.md', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extrait la section Contexte et les instructions principales
                context_match = re.search(r'## Contexte\n(.*?)\n\n', content, re.DOTALL)
                if context_match:
                    return context_match.group(1).strip()
                return "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."
        except Exception as e:
            logger.error(f"Erreur lors du chargement du prompt système: {str(e)}")
            return "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."

    async def ensure_connected(self):
        """S'assure que les connexions sont établies"""
        await self.mongo_ops.ensure_connected()
        if self.redis_ops:
            await self.redis_ops._init_redis()

    async def close_connections(self):
        """Ferme toutes les connexions"""
        await self.mongo_ops.close()
        if self.redis_ops:
            await self.redis_ops._close_redis()

    def _get_cache_key(self, query: str) -> str:
        """Génère une clé de cache normalisée pour une requête."""
        import hashlib
        qh = hashlib.sha1(f"{query}".encode("utf-8")).hexdigest()
        return f"rag:answer:{qh}"

    async def _get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Récupère une réponse en cache si disponible et non expirée."""
        if not self.redis_ops:
            return None
        
        try:
            cache_key = self._get_cache_key(query)
            cached_data = await self.redis_ops.redis.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                if datetime.fromisoformat(data["expires_at"]) > datetime.now():
                    await self.redis_ops.redis.expire(cache_key, self.response_cache_ttl)
                    response_data = data.get("response")
                    if isinstance(response_data, dict):
                        response_data = {**response_data, "cached": True}
                    else:
                        response_data = {"answer": response_data, "cached": True}
                    return response_data
                else:
                    await self.redis_ops.redis.delete(cache_key)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {str(e)}")
        return None

    async def _cache_response(self, query: str, response: Dict[str, Any]):
        """Met en cache une réponse avec expiration."""
        if not self.redis_ops:
            return
        
        try:
            cache_key = self._get_cache_key(query)
            expires_at = datetime.now() + timedelta(seconds=self.response_cache_ttl)
            
            serialisable_response = json.loads(json.dumps(response)) if isinstance(response, dict) else response
            data = {
                "response": serialisable_response,
                "expires_at": expires_at.isoformat(),
                "cached_at": datetime.now().isoformat()
            }
            
            async with self.redis_ops.redis.pipeline() as pipe:
                await pipe.setex(
                    cache_key,
                    self.response_cache_ttl,
                    json.dumps(data)
                )
                await pipe.zadd(
                    "rag:cache:stats",
                    {cache_key: datetime.now().timestamp()}
                )
                await pipe.execute()
                
            logger.debug(f"Réponse mise en cache pour la requête: {query[:50]}...")
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {str(e)}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Obtient l'embedding d'un texte via Ollama."""
        try:
            return await ollama_client.embed(text, rag_settings.EMBED_MODEL)
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding (Ollama): {str(e)}")
            raise

    def find_similar_documents(self, query_embedding: np.ndarray, k: int = 5) -> List[tuple]:
        """Trouve les k documents les plus similaires à la requête."""
        if self.embeddings_matrix is None or len(self.documents) == 0:
            return []
        
        # Calculer les similarités cosinus
        similarities = util.pytorch_cos_sim(
            query_embedding.reshape(1, -1),
            self.embeddings_matrix
        )[0]
        
        # Obtenir les k documents les plus similaires
        top_k_indices = np.argsort(similarities.numpy())[-k:][::-1]
        results = []
        for idx in top_k_indices:
            results.append((self.documents[idx], float(similarities[idx])))
        return results

    async def ingest_documents(self, directory: str):
        """Ingère des documents dans le système RAG."""
        try:
            await self.ensure_connected()
            start_time = datetime.now()
            # Lecture des documents
            documents: List[tuple[str, str]] = []
            for filename in os.listdir(directory):
                if not filename.endswith('.txt'):
                    continue
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        documents.append((filename, f.read()))
                except Exception as read_error:
                    logger.error("Erreur lecture document", file=file_path, error=str(read_error))

            # Découpage des documents en chunks
            chunks = []
            for filename, doc in documents:
                # Tokenization avec GPT2
                tokens = self.tokenizer.encode(doc)
                chunk_size = 512  # Taille de chunk en tokens
                overlap = 50     # Chevauchement en tokens
                
                for i in range(0, len(tokens), chunk_size - overlap):
                    chunk_tokens = tokens[i:i + chunk_size]
                    chunk_text = self.tokenizer.decode(chunk_tokens)
                    chunks.append((filename, chunk_text, i, i + len(chunk_tokens), len(tokens)))

            # Génération des embeddings et mise à jour de la matrice
            embeddings = []
            documents_to_persist = []
            for index, (filename, chunk_text, start_idx, end_idx, total_tokens) in enumerate(chunks):
                embedding = await self._get_embedding(chunk_text)
                embeddings.append(embedding)
                self.documents.append(chunk_text)

                # Préparer les données pour MongoDB
                document_dict = {
                    "content": chunk_text,
                    "source": filename,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_index": index,
                        "total_chunks": len(chunks),
                        "start_token": start_idx,
                        "end_token": end_idx,
                        "total_tokens": total_tokens
                    },
                    "created_at": datetime.now()
                }
                documents_to_persist.append(document_dict)

            # Sauvegarde en base (bulk)
            for document in documents_to_persist:
                await self.mongo_ops.save_document(PydanticDocument(**document))

            # Mise à jour de la matrice d'embeddings
            self.embeddings_matrix = np.array(embeddings).astype('float32')

            # Mise à jour des statistiques avec MongoDB
            await self._refresh_total_documents()

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Ingestion terminée en {processing_time:.2f} secondes")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des documents: {str(e)}")
            return False

    async def process_query(
        self,
        query: str,
        n_results: int = 5,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 500,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Traite une requête RAG et retourne une réponse structurée."""
        await self.ensure_connected()
        start_time = datetime.utcnow()
        cache_hit = False

        if use_cache:
            cached = await self._get_cached_response(query)
            if cached:
                cache_hit = True
                processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                cached.setdefault("processing_time_ms", processing_time_ms)
                cached.setdefault("sources", [])
                cached.setdefault("confidence_score", 0.0)
                cached.setdefault("cached", True)
                await self._record_query_history(query, cached, processing_time_ms, cache_hit)
                await self._update_system_stats(processing_time_ms, cache_hit)
                return cached

        query_embedding = await self._get_embedding(query)
        np_embedding = np.array(query_embedding, dtype=np.float32)
        k = max(1, int(rag_settings.RAG_TOPK)) if hasattr(rag_settings, "RAG_TOPK") else n_results
        similar_documents = self.find_similar_documents(np_embedding, min(n_results, k))
        context_docs = [doc for doc, _ in similar_documents]
        context_block = "\n\n---\n\n".join(context_docs)

        # Prompt strict RAG
        system = (self.system_prompt or "").strip()
        rag_instructions = (
            "You answer strictly from the provided CONTEXT.\n"
            "If missing, say you lack evidence. Language = fr.\n"
            "CONTEXT:\n" + context_block
        )
        prompt = (system + "\n\n" + rag_instructions + "\n\nQuestion: " + query).strip()

        answer = await ollama_client.generate(
            prompt=prompt,
            model=rag_settings.GEN_MODEL,
            temperature=temperature if temperature is not None else 0.2,
            max_tokens=max_tokens or 500,
            num_ctx=8192,
        )

        processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        sources = [
            {"content": doc, "similarity": float(score)}
            for doc, score in similar_documents
        ]
        confidence_values = [score for _, score in similar_documents]
        confidence = float(np.mean(confidence_values)) if confidence_values else 0.0

        response_payload = {
            "answer": answer,
            "sources": sources,
            "confidence_score": confidence,
            "processing_time_ms": processing_time_ms,
            "cached": cache_hit,
        }

        if use_cache:
            await self._cache_response(query, response_payload)

        await self._record_query_history(query, response_payload, processing_time_ms, cache_hit, context_docs)
        await self._update_system_stats(processing_time_ms, cache_hit)

        return response_payload

    async def query(self, query_text: str, top_k: int = 3) -> str:
        """Compatibilité : retourne uniquement la réponse textuelle."""
        result = await self.process_query(
            query=query_text,
            n_results=top_k,
            temperature=0.7,
            max_tokens=500,
            use_cache=True
        )
        return result.get("answer", "")

    async def _record_query_history(
        self,
        query: str,
        response_payload: Dict[str, Any],
        processing_time_ms: float,
        cache_hit: bool,
        context_docs: Optional[List[str]] = None
    ) -> None:
        """Persiste l'historique d'une requête."""
        try:
            history = PydanticQueryHistory(
                query=query,
                response=response_payload.get("answer", ""),
                context_docs=context_docs or [],
                processing_time=processing_time_ms / 1000.0,
                cache_hit=cache_hit,
                metadata={
                    "sources": response_payload.get("sources", []),
                    "confidence_score": response_payload.get("confidence_score", 0.0)
                }
            )
            await self.mongo_ops.save_query_history(history)
        except Exception as exc:
            logger.error(f"Erreur enregistrement historique RAG: {exc}")

    async def _update_system_stats(self, processing_time_ms: float, cache_hit: bool) -> None:
        """Met à jour les statistiques globales du système."""
        try:
            stats = await self.mongo_ops.get_system_stats()
            if not stats:
                stats = PydanticSystemStats(
                    total_documents=len(self.documents),
                    total_queries=0,
                    average_processing_time=0.0,
                    cache_hit_rate=0.0
                )

            previous_queries = stats.total_queries
            total_queries = previous_queries + 1
            total_cache_hits = int(stats.cache_hit_rate * previous_queries)
            if cache_hit:
                total_cache_hits += 1

            average_time_seconds = stats.average_processing_time
            new_average = (
                (average_time_seconds * previous_queries) + (processing_time_ms / 1000.0)
            ) / total_queries

            stats.total_queries = total_queries
            stats.average_processing_time = new_average
            stats.cache_hit_rate = total_cache_hits / total_queries if total_queries else 0.0
            stats.total_documents = max(stats.total_documents, len(self.documents))
            stats.last_update = datetime.utcnow()

            await self.mongo_ops.update_system_stats(stats)
        except Exception as exc:
            logger.error(f"Erreur mise à jour statistiques RAG: {exc}")

    async def _refresh_total_documents(self) -> None:
        """Met à jour le nombre total de documents indexés."""
        try:
            stats = await self.mongo_ops.get_system_stats()
            if not stats:
                stats = PydanticSystemStats(
                    total_documents=len(self.documents),
                    total_queries=0,
                    average_processing_time=0.0,
                    cache_hit_rate=0.0
                )
            stats.total_documents = len(self.documents)
            stats.last_update = datetime.utcnow()
            await self.mongo_ops.update_system_stats(stats)
        except Exception as exc:
            logger.error(f"Erreur mise à jour documents RAG: {exc}")

    async def index_content(
        self,
        content: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Indexe un contenu texte dans le système RAG."""
        await self.ensure_connected()
        metadata = metadata or {}
        document_id = metadata.get("document_id", str(uuid4()))

        tokens = self.tokenizer.encode(content)
        chunk_size = 512
        overlap = 50
        chunks_created = 0
        embeddings: List[List[float]] = []
        context_metadata: List[Dict[str, Any]] = []

        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens).strip()
            if not chunk_text:
                continue

            embedding = await self._get_embedding(chunk_text)
            embeddings.append(embedding)
            self.documents.append(chunk_text)

            document_metadata = {
                **metadata,
                "chunk_index": chunks_created,
                "start_token": i,
                "end_token": i + len(chunk_tokens),
                "total_tokens": len(tokens),
                "document_id": document_id
            }

            document = PydanticDocument(
                content=chunk_text,
                source=source,
                embedding=embedding,
                metadata=document_metadata
            )
            try:
                await self.mongo_ops.save_document(document)
            except Exception as exc:
                logger.error(f"Erreur sauvegarde document RAG: {exc}")

            context_metadata.append(document_metadata)
            chunks_created += 1

        if embeddings:
            embeddings_array = np.array(embeddings).astype("float32")
            if self.embeddings_matrix is None:
                self.embeddings_matrix = embeddings_array
            else:
                self.embeddings_matrix = np.vstack([self.embeddings_matrix, embeddings_array])

        await self._refresh_total_documents()

        return {
            "document_id": document_id,
            "chunks_created": chunks_created,
            "source": source,
            "metadata": context_metadata
        }

    async def ingest_documents_from_list(
        self,
        documents: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingestion de documents fournis en mémoire."""
        results = []
        for idx, content in enumerate(documents):
            source = (metadata or {}).get("source", f"doc_{idx}")
            result = await self.index_content(content, source, metadata)
            results.append(result)
        return {
            "ingested": len(results),
            "details": results
        }

    async def clear_cache(self) -> Dict[str, Any]:
        """Vide le cache des réponses RAG."""
        cleared = 0
        if self.redis_ops and self.redis_ops.redis:
            try:
                keys = await self.redis_ops.redis.keys("rag:response:*")
                if keys:
                    await self.redis_ops.redis.delete(*keys)
                    cleared = len(keys)
                await self.redis_ops.redis.delete("rag:cache:stats")
            except Exception as exc:
                logger.error(f"Erreur suppression cache RAG: {exc}")
        return {"cleared_entries": cleared}

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur le cache Redis."""
        stats = {
            "cached_entries": 0,
            "last_entries": []
        }
        if self.redis_ops and self.redis_ops.redis:
            try:
                keys = await self.redis_ops.redis.keys("rag:response:*")
                stats["cached_entries"] = len(keys)
                if keys:
                    sample_keys = keys[:5]
                    for key in sample_keys:
                        data = await self.redis_ops.redis.get(key)
                        if data:
                            payload = json.loads(data)
                            stats["last_entries"].append({
                                "key": key.decode() if hasattr(key, "decode") else str(key),
                                "cached_at": payload.get("cached_at"),
                                "expires_at": payload.get("expires_at")
                            })
            except Exception as exc:
                logger.error(f"Erreur lecture stats cache RAG: {exc}")
        return stats

    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques globales du système RAG."""
        stats = await self.mongo_ops.get_system_stats()
        if stats:
            return stats.model_dump()
        return {
            "total_documents": len(self.documents),
            "total_queries": 0,
            "average_processing_time": 0.0,
            "cache_hit_rate": 0.0,
            "last_update": datetime.utcnow().isoformat()
        }

    async def get_query_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Historique des requêtes récentes."""
        try:
            history = await self.mongo_ops.get_recent_queries(limit=limit)
            return [entry.model_dump() for entry in history]
        except Exception as exc:
            logger.error(f"Erreur récupération historique RAG: {exc}")
            return []

    async def validate_report(self, rapport: str) -> str:
        """Validation minimale d'un rapport via l'adaptateur principal."""
        messages = [
            {"role": "system", "content": "Analyse critique de rapport Lightning"},
            {"role": "user", "content": f"Rapport à analyser:\n\n{rapport}"}
        ]
        try:
            evaluation = await asyncio.to_thread(
                self.ai_adapter.generate_completion,
                messages=messages,
                temperature=0.3,
                max_tokens=600
            )
            return evaluation
        except Exception as exc:
            logger.error(f"Erreur validation rapport RAG: {exc}")
            return "Échec de la validation du rapport."

    async def validate_lightning_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validation basique d'une configuration Lightning."""
        issues = []
        if not config:
            issues.append("Configuration vide")
        if config and "fees" in config:
            fees = config["fees"]
            if isinstance(fees, dict):
                base_fee = fees.get("base") or fees.get("base_fee")
                if base_fee is not None and base_fee < 0:
                    issues.append("Base fee négative détectée")
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }

    async def update_embeddings(self):
        """Met à jour les embeddings pour les documents existants si nécessaire."""
        # Cette fonction nécessiterait de lire les documents depuis Prisma,
        # vérifier s'ils ont des embeddings, les générer et les mettre à jour.
        # La logique exacte dépendra de la façon dont les documents sont stockés initialement.
        logger.warning("La fonction update_embeddings n'est pas encore implémentée pour Prisma.")
        pass # À implémenter si nécessaire

    async def update_system_stats(self):
        """Met à jour les statistiques du système RAG."""
        # Cette fonction nécessiterait de lire les statistiques existantes depuis Prisma,
        # les mettre à jour et les enregistrer.
        # La logique exacte dépendra de la façon dont les statistiques sont stockées initialement.
        logger.warning("La fonction update_system_stats n'est pas encore implémentée pour Prisma.")
        pass # À implémenter si nécessaire 

    async def _init_redis(self):
        """Initialise les connexions Redis et MongoDB"""
        if self._init_task is None:
            self._init_task = asyncio.create_task(self.ensure_connected())
        await self._init_task

    async def close(self):
        """Ferme toutes les connexions"""
        await self.close_connections()
        if self._init_task:
            self._init_task.cancel()
            try:
                await self._init_task
            except asyncio.CancelledError:
                pass
            self._init_task = None 
