import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
from sentence_transformers import util
from transformers import GPT2Tokenizer
from openai import OpenAI
import redis.asyncio as redis
import asyncio
from .models import Document as PydanticDocument, QueryHistory as PydanticQueryHistory, SystemStats as PydanticSystemStats
from .mongo_operations import MongoOperations
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
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        
        # Configuration de la matrice d'embeddings
        self.dimension = 1536  # Dimension des embeddings OpenAI
        self.embeddings_matrix = None
        self.documents = []
        
        # Configuration Redis
        self.redis_ops = redis_ops
        self.response_cache_ttl = 3600  # 1 heure

        # Initialisation MongoDB
        self.mongo_ops = MongoOperations()

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
        await self.mongo_ops.initialize()
        if self.redis_ops:
            await self.redis_ops._init_redis()

    async def close_connections(self):
        """Ferme toutes les connexions"""
        await self.mongo_ops.close()
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
            documents = []
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                        documents.append(f.read())

            # Découpage des documents en chunks
            chunks = []
            for doc in documents:
                # Tokenization avec GPT2
                tokens = self.tokenizer.encode(doc)
                chunk_size = 512  # Taille de chunk en tokens
                overlap = 50     # Chevauchement en tokens
                
                for i in range(0, len(tokens), chunk_size - overlap):
                    chunk_tokens = tokens[i:i + chunk_size]
                    chunk_text = self.tokenizer.decode(chunk_tokens)
                    chunks.append(chunk_text)

            # Génération des embeddings et mise à jour de la matrice
            embeddings = []
            for chunk in chunks:
                embedding = await self._get_embedding(chunk)
                embeddings.append(embedding)
                self.documents.append(chunk)

                # Préparer les données pour MongoDB
                document_dict = {
                    "content": chunk,
                    "source": filename,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_index": len(embeddings) - 1,
                        "total_chunks": len(chunks)
                    },
                    "created_at": datetime.now()
                }
                # Sauvegarde avec MongoDB
                await self.mongo_ops.save_document(document_dict)

            # Mise à jour de la matrice d'embeddings
            self.embeddings_matrix = np.array(embeddings).astype('float32')

            # Mise à jour des statistiques avec MongoDB
            stats_dict = {
                'total_documents': len(self.documents),
                'total_queries': 0,
                'average_processing_time': 0.0,
                'cache_hit_rate': 0.0,
                'last_update': datetime.now()
            }
            await self.mongo_ops.update_system_stats(stats_dict)

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Ingestion terminée en {processing_time:.2f} secondes")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des documents: {str(e)}")
            return False

    async def query(self, query_text: str, top_k: int = 3) -> str:
        """Exécute une requête RAG."""
        try:
            await self.ensure_connected()
            start_time = datetime.now()

            # Vérifier le cache
            cached_response = await self._get_cached_response(query_text)
            if cached_response:
                # Mettre à jour les statistiques pour le cache hit
                stats = await self.mongo_ops.get_system_stats()
                if stats:
                    total_queries = stats.get('total_queries', 0) + 1
                    cache_hits = stats.get('cache_hits', 0) + 1
                    await self.mongo_ops.update_system_stats({
                        'total_queries': total_queries,
                        'cache_hits': cache_hits,
                        'cache_hit_rate': cache_hits / total_queries
                    })
                return cached_response

            # Générer l'embedding de la requête
            query_embedding = await self._get_embedding(query_text)

            # Recherche des documents similaires
            similar_documents = self.find_similar_documents(query_embedding, top_k)

            # Construire le contexte
            context = "\n\n---\n\n".join([doc for doc, _ in similar_documents])

            # Générer la réponse avec GPT
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query_text}"}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content

            # Mettre en cache la réponse
            await self._cache_response(query_text, answer)

            # Sauvegarder l'historique des requêtes
            query_history = {
                "query": query_text,
                "response": answer,
                "context": context,
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "created_at": datetime.now()
            }
            await self.mongo_ops.save_query_history(PydanticQueryHistory(**query_history))

            # Mettre à jour les statistiques
            stats = await self.mongo_ops.get_system_stats()
            if stats:
                total_queries = stats.get('total_queries', 0) + 1
                avg_time = stats.get('average_processing_time', 0.0)
                new_avg_time = (avg_time * (total_queries - 1) + query_history['processing_time']) / total_queries
                cache_hits = stats.get('cache_hits', 0)
                
                await self.mongo_ops.update_system_stats({
                    'total_queries': total_queries,
                    'average_processing_time': new_avg_time,
                    'cache_hit_rate': cache_hits / total_queries,
                    'last_query': datetime.now()
                })

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
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