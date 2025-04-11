import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import asyncio
from sentence_transformers import util
from transformers import GPT2Tokenizer
from openai import OpenAI
import redis.asyncio as redis

from .models import Document as PydanticDocument, QueryHistory as PydanticQueryHistory, SystemStats as PydanticSystemStats
from .mongo_operations import MongoOperations
from .redis_operations import RedisOperations
from .embeddings.batch_embeddings import BatchEmbeddings
from .embeddings.vector_index import VectorIndex
from .cache.smart_cache import SmartCache
from .utils.async_utils import async_timed, AsyncBatchProcessor, RetryWithBackoff

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGError(Exception):
    """Erreur personnalisée pour le RAG"""
    pass

class Heuristic:
    """Classe pour gérer les scores heuristiques"""
    def __init__(self, weight: float, lower_is_better: bool):
        self.lowest = float('inf')
        self.highest = float('-inf')
        self.weight = weight
        self.lower_is_better = lower_is_better

    def update(self, value: float):
        if value > self.highest:
            self.highest = value
        if value < self.lowest:
            self.lowest = value

    def get_score(self, value: float) -> float:
        if self.highest == self.lowest:
            return self.weight
        score = (value - self.lowest) / (self.highest - self.lowest)
        if self.lower_is_better:
            return (1 - score) * self.weight
        return score * self.weight

class RAGWorkflow:
    def __init__(self, redis_ops: Optional[RedisOperations] = None, similarity_top_k: int = 3, streaming: bool = True):
        # Initialisation du client OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Chargement du prompt système
        self.system_prompt = self._load_system_prompt()
        
        # Configuration du tokenizer
        self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        
        # Initialisation des services optimisés
        self.redis_ops = redis_ops
        self.mongo_ops = MongoOperations()
        self._init_task = None
        
        # Initialiser le gestionnaire d'embeddings par lot
        self.batch_embeddings = BatchEmbeddings()
        
        # Initialiser l'index vectoriel
        self.vector_index = VectorIndex(dimension=1536)
        
        # Initialiser le cache intelligent si Redis est disponible
        self.smart_cache = None
        if redis_ops:
            self.smart_cache = SmartCache(redis_ops.redis)
        
        # Initialiser le processeur de lots asynchrone
        self.batch_processor = AsyncBatchProcessor(batch_size=50, max_workers=3)
        
        # Initialiser le gestionnaire de retry
        self.retry_manager = RetryWithBackoff(max_retries=3, initial_delay=1.0)

        # Configuration flexible
        self.similarity_top_k = similarity_top_k
        self.streaming = streaming

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

    @async_timed()
    async def ingest_documents(self, directory: str) -> bool:
        """
        Ingère des documents dans le système RAG.
        Utilise le traitement par lot et parallèle pour optimiser les performances.
        
        Args:
            directory: Chemin vers le répertoire contenant les documents
            
        Returns:
            True si succès, False sinon
        """
        if not os.path.exists(directory):
            raise RAGError(f"Le répertoire {directory} n'existe pas.")
        try:
            await self.ensure_connected()
            start_time = datetime.now()
            
            # Lecture des documents
            documents = []
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                        content = f.read()
                        documents.append({
                            "content": content,
                            "source": filename
                        })
            
            logger.info(f"Découpage de {len(documents)} documents en chunks")
            
            # Fonction pour découper un document en chunks
            def split_document(doc: Dict[str, str]) -> List[Dict[str, Any]]:
                content = doc["content"]
                source = doc["source"]
                
                # Tokenization avec GPT2
                tokens = self.tokenizer.encode(content)
                chunk_size = 512  # Taille de chunk en tokens
                overlap = 50     # Chevauchement en tokens
                
                chunks = []
                for i in range(0, len(tokens), chunk_size - overlap):
                    chunk_tokens = tokens[i:i + chunk_size]
                    chunk_text = self.tokenizer.decode(chunk_tokens)
                    chunks.append({
                        "content": chunk_text,
                        "source": source,
                        "chunk_index": len(chunks),
                        "created_at": datetime.now()
                    })
                
                return chunks
            
            # Découper tous les documents en chunks en parallèle
            all_chunks = []
            for doc in documents:
                chunks = split_document(doc)
                all_chunks.extend(chunks)
            
            # Traitement par lots
            logger.info(f"Génération d'embeddings pour {len(all_chunks)} chunks")
            
            # Fonction pour traiter un lot de chunks
            async def process_chunk_batch(chunk_batch: List[Dict]) -> List[Dict]:
                # Extraire les textes pour l'embedding
                texts = [chunk["content"] for chunk in chunk_batch]
                
                # Générer les embeddings en lot
                embeddings = await self.batch_embeddings.get_embeddings_with_retry(texts)
                
                # Ajouter les embeddings aux chunks et sauvegarder dans MongoDB
                processed_chunks = []
                for i, (chunk, embedding) in enumerate(zip(chunk_batch, embeddings)):
                    chunk["embedding"] = embedding
                    # Sauvegarder dans MongoDB
                    await self.mongo_ops.save_document(chunk)
                    processed_chunks.append(chunk)
                
                return processed_chunks
            
            # Traitement par lot avec le processeur asynchrone
            processed_chunks = await self.batch_processor.process_batches_parallel(
                all_chunks, 
                process_chunk_batch
            )
            
            # Ajouter les chunks traités à l'index vectoriel
            chunk_texts = [chunk["content"] for chunk in processed_chunks]
            chunk_embeddings = [chunk["embedding"] for chunk in processed_chunks]
            
            # Créer ou mettre à jour l'index
            self.vector_index.add_documents(processed_chunks, chunk_embeddings)
            
            # Sauvegarder l'index
            os.makedirs("data/indexes", exist_ok=True)
            self.vector_index.save("data/indexes/main_index")
            
            # Mise à jour des statistiques
            stats_dict = {
                'total_documents': len(processed_chunks),
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

    @async_timed()
    async def query(self, query_text: str, top_k: int = 3) -> str:
        """
        Exécute une requête RAG avec optimisations.
        
        Args:
            query_text: Texte de la requête
            top_k: Nombre de documents similaires à récupérer
            
        Returns:
            Réponse générée
        """
        if not query_text:
            raise RAGError("Le texte de la requête ne peut pas être vide.")

        # Initialiser l'heuristique pour la requête
        query_heuristic = Heuristic(weight=1.0, lower_is_better=False)
        query_heuristic.update(len(query_text))
        query_score = query_heuristic.get_score(len(query_text))

        # Ajuster dynamiquement top_k en fonction du score de la requête
        adjusted_top_k = max(1, int(top_k * query_score))

        try:
            await self.ensure_connected()
            start_time = datetime.now()
            
            # Vérifier le cache intelligent
            if self.smart_cache:
                # Clé unique pour cette requête spécifique
                cache_key = {"query": query_text, "top_k": adjusted_top_k}
                
                # Tentative de récupération depuis le cache
                cached_response = await self.smart_cache.get("responses", cache_key)
                if cached_response:
                    logger.info(f"Réponse récupérée du cache pour: {query_text[:50]}...")
                    
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
            
            # Obtenir l'embedding de la requête
            query_embedding = await self.retry_manager.execute(
                self.batch_embeddings.embeddings.embed_query,
                query_text
            )
            
            # Recherche des documents similaires avec l'index vectoriel
            similar_documents = self.vector_index.search(query_embedding, k=adjusted_top_k)
            
            # Évaluer les documents récupérés
            document_heuristic = Heuristic(weight=1.0, lower_is_better=True)
            for doc, _ in similar_documents:
                document_heuristic.update(len(doc.get('content', '')))

            # Sélectionner les documents basés sur les scores heuristiques
            selected_documents = [doc for doc, _ in similar_documents
                                  if document_heuristic.get_score(len(doc.get('content', ''))) > 0.5]
            
            # Construire le contexte
            context = "\n\n".join([
                f"[Document {i+1}] {doc.get('content', '')}"
                for i, doc in enumerate(selected_documents)
            ])
            
            # Construire le prompt pour l'API de complétion
            prompt = f"""Contexte:
{context}

Question: {query_text}

Réponds de manière concise et précise à la question en te basant uniquement sur le contexte fourni.
Si le contexte ne contient pas suffisamment d'informations pour répondre, indique-le clairement."""
            
            # Génération de la réponse par le LLM - avec retry en cas d'échec
            async def generate_completion():
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                return response.choices[0].message.content
            
            response = await self.retry_manager.execute(generate_completion)
            
            # Sauvegarder dans le cache intelligent avec tags contextuels
            if self.smart_cache:
                # Créer des tags basés sur les sources de documents utilisés
                doc_sources = [doc.get('source', 'unknown') for doc in selected_documents]
                
                # Tags pour l'invalidation ciblée
                tags = [f"source:{source}" for source in set(doc_sources)]
                tags.append(f"date:{datetime.now().strftime('%Y-%m-%d')}")
                tags.append("type:rag_response")
                
                await self.smart_cache.set(
                    "responses", 
                    cache_key, 
                    response, 
                    tags=tags
                )
            
            # Enregistrement de l'historique des requêtes
            query_history = {
                "query": query_text,
                "timestamp": datetime.now(),
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "num_results": len(selected_documents)
            }
            await self.mongo_ops.save_query_history(query_history)
            
            # Mise à jour des statistiques
            stats = await self.mongo_ops.get_system_stats()
            if stats:
                total_queries = stats.get('total_queries', 0) + 1
                avg_time = stats.get('average_processing_time', 0)
                new_avg_time = ((avg_time * (total_queries - 1)) + 
                              (datetime.now() - start_time).total_seconds()) / total_queries
                
                await self.mongo_ops.update_system_stats({
                    'total_queries': total_queries,
                    'average_processing_time': new_avg_time,
                    'last_query': datetime.now()
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la requête RAG: {str(e)}")
            raise

    async def update_embeddings(self):
        """Met à jour les embeddings de tous les documents."""
        # À implémenter
        pass

    async def update_system_stats(self):
        """Met à jour les statistiques du système."""
        # À implémenter
        pass

    async def close(self):
        """Ferme toutes les connexions."""
        await self.close_connections()

    async def cleanup(self):
        """Libère les ressources et ferme les connexions"""
        await self.close_connections()
        self.vector_index = None
        self.batch_embeddings = None
        self.smart_cache = None
        logger.info("Ressources libérées et connexions fermées") 