import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import faiss
from openai import OpenAI
import redis.asyncio as redis
from tiktoken import encoding_for_model
from langchain.text_splitter import TokenTextSplitter
import asyncio
from .models import Document as PydanticDocument, QueryHistory as PydanticQueryHistory, SystemStats as PydanticSystemStats
from .prisma_operations import PrismaOperations
from .redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGWorkflow:
    def __init__(self, redis_ops: Optional[RedisOperations] = None):
        # Initialisation du client OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Chargement du prompt système
        self.system_prompt = self._load_system_prompt()
        
        # Configuration du tokenizer
        self.tokenizer = encoding_for_model("gpt-3.5-turbo")
        
        # Configuration du text splitter
        self.text_splitter = TokenTextSplitter(
            chunk_size=512,
            chunk_overlap=50
        )
        
        # Initialisation de FAISS
        self.dimension = 1536  # Dimension des embeddings OpenAI
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        
        # Configuration Redis
        self.redis_ops = redis_ops
        self.response_cache_ttl = 3600  # 1 heure

        # Initialisation Prisma
        self.prisma_ops = PrismaOperations()

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

    async def _init_redis(self):
        """Initialise la connexion Redis."""
        if self.redis_ops:
            await self.redis_ops._init_redis()

    async def _close_redis(self):
        """Ferme la connexion Redis."""
        if self.redis_ops:
            await self.redis_ops._close_redis()

    def _get_cache_key(self, query: str) -> str:
        """Génère une clé de cache pour une requête."""
        return f"rag:response:{hash(query)}"

    async def _get_cached_response(self, query: str) -> Optional[str]:
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
                    return data["response"]
                else:
                    await self.redis_ops.redis.delete(cache_key)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {str(e)}")
        return None

    async def _cache_response(self, query: str, response: str):
        """Met en cache une réponse avec expiration."""
        if not self.redis_ops:
            return
        
        try:
            cache_key = self._get_cache_key(query)
            expires_at = datetime.now() + timedelta(seconds=self.response_cache_ttl)
            
            data = {
                "response": response,
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
        """Obtient l'embedding d'un texte via l'API OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {str(e)}")
            raise

    async def ingest_documents(self, directory: str):
        """Ingère des documents dans le système RAG."""
        try:
            await self.prisma_ops.ensure_connected()
            start_time = datetime.now()
            # Lecture des documents
            documents = []
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                        documents.append(f.read())

            # Découpage des documents en chunks
            chunks = []
            for doc in documents:
                # Découpage en tokens
                tokens = self.tokenizer.encode(doc)
                chunk_size = 512  # Taille de chunk en tokens
                overlap = 50     # Chevauchement en tokens
                
                for i in range(0, len(tokens), chunk_size - overlap):
                    chunk_tokens = tokens[i:i + chunk_size]
                    chunk_text = self.tokenizer.decode(chunk_tokens)
                    chunks.append(chunk_text)

            # Génération des embeddings et mise à jour de FAISS
            embeddings = []
            for chunk in chunks:
                embedding = await self._get_embedding(chunk)
                embeddings.append(embedding)
                self.documents.append(chunk)

                # Préparer les données pour Prisma
                document_dict = {
                    "content": chunk,
                    "source": filename,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_index": len(embeddings) - 1,
                        "total_chunks": len(chunks)
                    }
                }
                # Sauvegarde avec Prisma
                await self.prisma_ops.save_document(document_dict)

            # Mise à jour de l'index FAISS
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)

            # Mise à jour des statistiques avec Prisma
            stats_dict = {
                'total_documents': self.index.ntotal,
                'total_queries': 0,
                'average_processing_time': 0.0,
                'cache_hit_rate': 0.0
            }
            # Lire les stats existantes pour mettre à jour total_queries etc.
            existing_stats = await self.prisma_ops.get_system_stats()
            if existing_stats:
                stats_dict['total_queries'] = existing_stats.total_queries
                stats_dict['average_processing_time'] = existing_stats.average_processing_time
                stats_dict['cache_hit_rate'] = existing_stats.cache_hit_rate
            
            # Incrémenter total_documents (ou le définir si c'est la première ingestion)
            stats_dict['total_documents'] = self.index.ntotal

            await self.prisma_ops.update_system_stats(stats_dict)

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Documents ingérés avec succès: {len(chunks)} chunks en {processing_time:.2f} secondes")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des documents: {str(e)}")
            raise

    async def query(self, query_text: str, top_k: int = 3) -> str:
        """Effectue une requête RAG complète."""
        try:
            start_time = datetime.now()
            # Vérification du cache
            cached_response = await self._get_cached_response(query_text)
            cache_hit = cached_response is not None
            if cache_hit:
                return cached_response

            # Si l'index est vide, utiliser directement le texte de la requête
            if len(self.documents) == 0:
                # Appel à l'API OpenAI avec le prompt système chargé
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": query_text}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                answer = response.choices[0].message.content
                return answer

            # Génération de l'embedding de la requête
            query_embedding = await self._get_embedding(query_text)
            query_embedding_array = np.array([query_embedding]).astype('float32')

            # Recherche des documents les plus pertinents
            distances, indices = self.index.search(query_embedding_array, min(top_k, len(self.documents)))
            
            # Récupération des documents pertinents
            relevant_docs = [self.documents[i] for i in indices[0]]
            
            # Construction du prompt pour OpenAI
            context = "\n\n".join(relevant_docs)
            prompt = f"""En utilisant le contexte suivant, réponds à la question de manière précise et concise.

Contexte:
{context}

Question: {query_text}

Réponse:"""

            # Appel à l'API OpenAI avec le prompt système chargé
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content

            # Mise en cache de la réponse
            await self._cache_response(query_text, answer)

            # Sauvegarde de l'historique avec Prisma
            history_entry = {
                "query": query_text,
                "response": answer,
                "context_docs": [doc[:100] + '...' for doc in relevant_docs],
                "processing_time": processing_time,
                "cache_hit": cache_hit,
                "metadata": {
                    "model": "gpt-3.5-turbo",
                    "top_k": top_k
                }
            }
            await self.prisma_ops.save_query_history(history_entry)

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de la requête RAG: {str(e)}")
            # Sauvegarde de l'erreur dans l'historique
            processing_time = (datetime.now() - start_time).total_seconds()
            history_entry = {
                "query": query_text,
                "response": f"Erreur: {str(e)}",
                "context_docs": [],
                "processing_time": processing_time,
                "cache_hit": cache_hit,
                "metadata": {"error": True}
            }
            await self.prisma_ops.save_query_history(history_entry)
            raise

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