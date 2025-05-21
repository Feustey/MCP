import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import httpx
import redis.asyncio as redis
from tiktoken import encoding_for_model
import asyncio
from rag.models import Document, QueryHistory, SystemStats
from rag.mongo_operations import MongoOperations
from src.llm_selector import get_llm, ask_llm_choice
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, Filter

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaEmbedder:
    """Classe dédiée à la génération d'embeddings via Ollama."""
    
    def __init__(self, model="llama3", dimension=384):
        self.model = model
        self.dimension = dimension
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
    async def get_embedding(self, text: str, max_retries=3) -> List[float]:
        """
        Obtient l'embedding d'un texte via Ollama avec mécanisme de retry.
        """
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/api/embeddings"
                data = {
                    "model": self.model,
                    "prompt": text
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    result = response.json()
                    return result.get("embedding", [])
                    
            except Exception as e:
                logger.error(f"Tentative {attempt+1}/{max_retries}: Erreur lors de la génération de l'embedding: {str(e)}")
                if attempt == max_retries - 1:
                    # Retourner un embedding vide plutôt que de lever une exception
                    return np.zeros(self.dimension).tolist()
                await asyncio.sleep(1)

class DocumentStore:
    """Classe pour gérer le stockage et la recherche de documents avec Qdrant (vector store, remplace FAISS)."""
    
    def __init__(self, embedder: OllamaEmbedder, mongo_ops: MongoOperations):
        self.embedder = embedder
        self.mongo_ops = mongo_ops
        self.dimension = embedder.dimension
        self.documents = []
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.tokenizer = encoding_for_model("gpt-3.5-turbo")
        # Initialisation Qdrant
        self.qdrant = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=int(os.getenv("QDRANT_PORT", 6333)))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "mcp_rag")
        self._ensure_collection()

    def _ensure_collection(self):
        # Crée la collection si elle n'existe pas
        if self.collection_name not in [c.name for c in self.qdrant.get_collections().collections]:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE)
            )

    def _split_text(self, text: str) -> List[str]:
        tokens = self.tokenizer.encode(text)
        chunks = []
        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        return chunks

    async def add_document(self, text: str, source: str, metadata: Dict = None) -> bool:
        try:
            chunks = self._split_text(text)
            points = []
            for i, chunk in enumerate(chunks):
                embedding = await self.embedder.get_embedding(chunk)
                self.documents.append(chunk)
                meta = metadata or {}
                meta.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source": source
                })
                # Sauvegarde dans MongoDB
                document = Document(
                    content=chunk,
                    source=source,
                    embedding=embedding,
                    metadata=meta
                )
                await self.mongo_ops.save_document(document)
                # Prépare le point pour Qdrant
                points.append(PointStruct(
                    id=f"{source}_{i}_{datetime.now().timestamp()}",
                    vector=embedding,
                    payload=meta
                ))
            # Ajout en batch dans Qdrant
            if points:
                self.qdrant.upsert(collection_name=self.collection_name, points=points)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du document dans Qdrant: {str(e)}")
            return False

    async def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Dict]:
        try:
            # Qdrant attend une liste python, pas un np.ndarray
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.flatten().tolist()
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            docs = []
            for hit in results:
                docs.append({
                    "content": hit.payload.get("content", ""),
                    "score": hit.score,
                    "index": hit.id,
                    "metadata": hit.payload
                })
            return docs
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Qdrant: {str(e)}")
            return []

class SemanticCache:
    """Classe pour gérer le cache sémantique des requêtes et réponses."""
    
    def __init__(self, embedder: OllamaEmbedder, redis_url: str = None):
        self.embedder = embedder
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.response_cache_ttl = 3600  # 1 heure
        self.similarity_threshold = 0.85  # Seuil de similarité pour considérer une requête comme similaire
        
    async def _init_redis(self):
        """Initialise la connexion Redis."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url)
            
    async def _close_redis(self):
        """Ferme la connexion Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        except Exception:
            return 0.0
    
    async def get_semantic_key(self, query: str) -> str:
        """Génère une clé de cache sémantique pour une requête."""
        query_embedding = await self.embedder.get_embedding(query)
        # Utiliser les 8 premiers éléments comme signature
        signature = [round(x, 4) for x in query_embedding[:8]]
        return f"rag:semantic:{hash(str(signature))}"
    
    async def get_cached_response(self, query: str) -> Optional[Dict]:
        """Récupère une réponse en cache si disponible et sémantiquement similaire."""
        if not self.redis_client:
            await self._init_redis()
            if not self.redis_client:
                return None
        
        try:
            # Obtenir l'embedding de la requête
            query_embedding = await self.embedder.get_embedding(query)
            
            # Récupérer toutes les entrées du cache
            cache_keys = await self.redis_client.keys("rag:response:*")
            
            for key in cache_keys:
                cached_data_raw = await self.redis_client.get(key)
                if not cached_data_raw:
                    continue
                    
                cached_data = json.loads(cached_data_raw)
                cached_embedding = cached_data.get("query_embedding")
                
                # Si pas d'embedding ou expiré, ignorer
                if not cached_embedding or datetime.fromisoformat(cached_data["expires_at"]) <= datetime.now():
                    await self.redis_client.delete(key)
                    continue
                
                # Calculer la similarité
                similarity = self._calculate_similarity(query_embedding, cached_embedding)
                
                if similarity >= self.similarity_threshold:
                    # Prolonger l'expiration
                    await self.redis_client.expire(key, self.response_cache_ttl)
                    return {
                        "answer": cached_data["response"],
                        "source": "semantic_cache",
                        "similarity": similarity
                    }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache sémantique: {str(e)}")
        
        return None
            
    async def cache_response(self, query: str, response: str):
        """Met en cache une réponse avec son embedding pour recherche sémantique future."""
        if not self.redis_client:
            await self._init_redis()
            if not self.redis_client:
                return
        
        try:
            # Générer l'embedding de la requête
            query_embedding = await self.embedder.get_embedding(query)
            cache_key = await self.get_semantic_key(query)
            expires_at = datetime.now() + timedelta(seconds=self.response_cache_ttl)
            
            data = {
                "response": response,
                "query": query,
                "query_embedding": query_embedding,
                "expires_at": expires_at.isoformat(),
                "cached_at": datetime.now().isoformat()
            }
            
            async with self.redis_client.pipeline() as pipe:
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
                
            logger.debug(f"Réponse mise en cache sémantique pour la requête: {query[:50]}...")
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache sémantique: {str(e)}")

class ConfigurationValidator:
    """Classe pour valider les configurations proposées."""
    
    def __init__(self, llm):
        self.llm = llm
        
    async def validate_lightning_config(self, config: Dict) -> Dict:
        """Valide une configuration de nœud Lightning en vérifiant sa cohérence avec les bonnes pratiques."""
        prompt = f"""
        Évalue si cette configuration respecte les bonnes pratiques du Lightning Network:
        {json.dumps(config, indent=2)}
        
        Points à vérifier:
        1. Le temps de réponse HTLC cible est-il réaliste? (optimal: 0.3s)
        2. La gestion de liquidité est-elle équilibrée? (minimum 66% canaux liquides)
        3. Les frais sont-ils compétitifs sans être trop bas?
        4. La stratégie de connexion aux autres nœuds est-elle pertinente?
        
        Réponds UNIQUEMENT au format JSON avec:
        {{"score": 0-10, "feedback": "Commentaire détaillé", "improvements": ["suggestion1", "suggestion2"]}}
        """
        
        try:
            result = await self.llm.generate(prompt)
            response_text = result.get("text", "")
            
            # Extraire le JSON de la réponse
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                validation_result = json.loads(json_match.group(0))
                return validation_result
            else:
                return {
                    "score": 5,
                    "feedback": "Impossible d'analyser la réponse",
                    "improvements": ["Vérifier manuellement la configuration"]
                }
        except Exception as e:
            logger.error(f"Erreur lors de la validation de la configuration: {str(e)}")
            return {
                "score": 0,
                "feedback": f"Erreur technique: {str(e)}",
                "improvements": ["Réessayer la validation"]
            }

class RAGWorkflow:
    """Classe principale orchestrant le workflow RAG complet."""
    
    def __init__(self, llm=None, redis_ops=None):
        # Initialisation du LLM
        if llm is None:
            choice = ask_llm_choice()
            llm = get_llm(choice)
        self.llm = llm
        
        # Initialisation des composants
        self.embedder = OllamaEmbedder()
        self.mongo_ops = MongoOperations()
        self.document_store = DocumentStore(self.embedder, self.mongo_ops)
        self.cache = SemanticCache(self.embedder)
        self.validator = ConfigurationValidator(llm)
        self.redis_ops = redis_ops
        
        # Chargement du prompt système
        self.system_prompt = self._load_system_prompt()
        self._init_task = None
        
    async def ensure_connected(self):
        """S'assure que toutes les connexions sont établies."""
        if hasattr(self.mongo_ops, 'connect'):
            await self.mongo_ops.connect()
        if hasattr(self.cache, '_init_redis'):
            await self.cache._init_redis()
        if self.redis_ops and hasattr(self.redis_ops, '_init_redis'):
            await self.redis_ops._init_redis()
        return True
        
    async def close_connections(self):
        """Ferme proprement toutes les connexions."""
        if hasattr(self.mongo_ops, 'close'):
            await self.mongo_ops.close()
        if hasattr(self.cache, '_close_redis'):
            await self.cache._close_redis()
        if self.redis_ops and hasattr(self.redis_ops, '_close_redis'):
            await self.redis_ops._close_redis()
        return True
    
    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis une chaîne de caractères."""
        try:
            content = """# Prompt RAG pour Analyse Sparkseer

## Contexte
Vous êtes un assistant expert en analyse du réseau Lightning et en traitement de données. Votre rôle est d'analyser les données fournies par l'API Sparkseer et de générer des insights pertinents en utilisant une approche RAG (Retrieval-Augmented Generation)."""
            
            # Extrait la section Contexte et les instructions principales
            context_match = re.search(r'## Contexte\n(.*?)\n\n', content, re.DOTALL)
            if context_match:
                return context_match.group(1).strip()
            return "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."
        except Exception as e:
            logger.error(f"Erreur lors du chargement du prompt système: {str(e)}")
            return "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."

    async def ingest_documents(self, directory: str):
        """Ingère des documents dans le système RAG et retourne un résumé structuré."""
        try:
            start_time = datetime.now()
            documents = []
            total_chunks = 0
            errors = 0
            for filename in os.listdir(directory):
                if filename.endswith(('.txt', '.md')):
                    try:
                        with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Ajout du document (peut générer plusieurs chunks)
                            result = await self.document_store.add_document(
                                text=content,
                                source=filename,
                                metadata={"origin": directory}
                            )
                            documents.append(filename)
                            # On estime le nombre de chunks ajoutés (via split_text)
                            total_chunks += len(self.document_store._split_text(content))
                    except Exception as e:
                        logger.error(f"Erreur lors de l'ingestion du fichier {filename}: {str(e)}")
                        errors += 1

            # Mise à jour des statistiques
            stats = await self.mongo_ops.get_system_stats() or SystemStats()
            stats.total_documents += len(documents)
            stats.last_updated = datetime.now()
            await self.mongo_ops.update_system_stats(stats)

            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Documents ingérés avec succès: {len(documents)} documents en {processing_time:.2f} secondes")
            return {
                "documents_processed": len(documents),
                "chunks_created": total_chunks,
                "processing_time": processing_time,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des documents: {str(e)}")
            return {
                "documents_processed": 0,
                "chunks_created": 0,
                "processing_time": 0.0,
                "errors": 1,
                "error_message": str(e)
            }

    async def validate_report_with_ollama(self, rapport: str) -> str:
        """Valide un rapport généré en utilisant Ollama."""
        ollama = get_llm("ollama")
        prompt = (
            "[INST] <<SYS>>\n"
            "Vous êtes un expert du réseau Lightning et un relecteur critique.\n"
            "Votre tâche est d'évaluer la qualité du rapport ci-dessous, généré par un autre modèle.\n"
            "- Analysez la clarté, la structure, la pertinence des recommandations et la justesse des analyses.\n"
            "- Relevez les points forts et les points faibles.\n"
            "- Suggérez des améliorations concrètes si nécessaire.\n"
            "- Répondez uniquement en français.\n"
            "<</SYS>>\n\n"
            "# Rapport à évaluer\n\n"
            f"{rapport}\n\n"
            "# Votre évaluation"
        )
        response = await ollama.acomplete(system_prompt="", prompt=prompt)
        return response.text if hasattr(response, 'text') else str(response)

    async def validate_lightning_config(self, config: Dict) -> Dict:
        """Valide une configuration de nœud Lightning Network."""
        return await self.validator.validate_lightning_config(config)

    async def query(self, query_text: str, top_k: int = 3) -> dict:
        """Exécute une requête RAG avec cache sémantique."""
        try:
            # Vérifier le cache sémantique
            cached_response = await self.cache.get_cached_response(query_text)
            if cached_response:
                return cached_response

            # Générer l'embedding de la requête
            query_embedding = await self.embedder.get_embedding(query_text)
            query_embedding = np.array([query_embedding]).astype('float32')

            # Rechercher les documents similaires
            results = await self.document_store.search(query_embedding, top_k)
            
            if not results:
                # Aucun document pertinent trouvé
                response = await self.llm.generate(
                    f"La requête suivante n'a pas trouvé de documents pertinents: '{query_text}'. "
                    "Réponds du mieux que tu peux avec tes connaissances générales."
                )
                answer = response.get("text", "")
            else:
                # Construire le prompt avec le contexte
                context_docs = [result["content"] for result in results]
                context = "\n\n---\n\n".join(context_docs)
                
                prompt = f"""Contexte:
```
{context}
```

Question: {query_text}

Réponds de manière précise et détaillée en te basant uniquement sur le contexte fourni.
Si le contexte ne contient pas l'information nécessaire, indique-le clairement.
"""
                
                response = await self.llm.generate(prompt)
                answer = response.get("text", "")
            
            # Mettre en cache la réponse
            await self.cache.cache_response(query_text, answer)
            
            # Enregistrer l'historique
            history = QueryHistory(
                query=query_text,
                response=answer,
                timestamp=datetime.now()
            )
            await self.mongo_ops.save_query_history(history)
            
            return {
                "answer": answer,
                "source": "rag"
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête RAG: {str(e)}")
            return {
                "answer": f"Je suis désolé, une erreur s'est produite lors du traitement de votre requête.",
                "source": "error",
                "error": str(e)
            }

if __name__ == "__main__":
    import time
    import os
    
    print("RAG Worker démarré en mode service")
    
    # Vérifie si on doit exécuter en mode ponctuel ou service
    run_once = os.environ.get('RAG_RUN_ONCE', 'false').lower() == 'true'
    
    if run_once:
        # Mode ponctuel : exécute une fois et sort
        workflow = RAGWorkflow()
        workflow.run()
        print("Exécution ponctuelle terminée")
    else:
        # Mode service : exécute périodiquement
        interval = int(os.environ.get('RAG_INTERVAL_SECONDS', '3600'))  # Par défaut toutes les heures
        
        print(f"Mode service actif - intervalle: {interval} secondes")
        
        while True:
            try:
                workflow = RAGWorkflow()
                workflow.run()
                print(f"Cycle terminé, attente de {interval} secondes avant le prochain cycle")
            except Exception as e:
                print(f"Erreur pendant l'exécution: {str(e)}")
                
            time.sleep(interval) 