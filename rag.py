import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import faiss
from openai import OpenAI
import redis.asyncio as redis
from llama_index.core.schema import NodeWithScore
from llama_index.core.text_splitter import TokenTextSplitter
from llama_index.core.node_parser import SimpleNodeParser

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGWorkflow:
    def __init__(self):
        # Initialisation du client OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Configuration du text splitter
        self.text_splitter = TokenTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separator="\n"
        )
        
        # Configuration du node parser
        self.node_parser = SimpleNodeParser.from_defaults(
            text_splitter=self.text_splitter
        )
        
        # Initialisation de FAISS
        self.dimension = 1536  # Dimension des embeddings OpenAI
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        
        # Configuration Redis
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.response_cache_ttl = 3600  # 1 heure

    async def _init_redis(self):
        """Initialise la connexion Redis."""
        if not self.redis_client:
            self.redis_client = redis.from_url(self.redis_url)

    async def _close_redis(self):
        """Ferme la connexion Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    def _get_cache_key(self, query: str) -> str:
        """Génère une clé de cache pour une requête."""
        return f"rag:response:{hash(query)}"

    async def _get_cached_response(self, query: str) -> Optional[str]:
        """Récupère une réponse en cache si disponible et non expirée."""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(query)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                if datetime.fromisoformat(data["expires_at"]) > datetime.now():
                    await self.redis_client.expire(cache_key, self.response_cache_ttl)
                    return data["response"]
                else:
                    await self.redis_client.delete(cache_key)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du cache: {str(e)}")
        return None

    async def _cache_response(self, query: str, response: str):
        """Met en cache une réponse avec expiration."""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(query)
            expires_at = datetime.now() + timedelta(seconds=self.response_cache_ttl)
            
            data = {
                "response": response,
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
                
            logger.debug(f"Réponse mise en cache pour la requête: {query[:50]}...")
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {str(e)}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Obtient l'embedding d'un texte via l'API OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
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
            # Lecture des documents
            documents = []
            for filename in os.listdir(directory):
                if filename.endswith('.txt'):
                    with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                        documents.append(f.read())

            # Parsing des documents en chunks
            nodes = []
            for doc in documents:
                nodes.extend(self.node_parser.get_nodes_from_documents([doc]))

            # Génération des embeddings et mise à jour de FAISS
            embeddings = []
            for node in nodes:
                embedding = await self._get_embedding(node.text)
                embeddings.append(embedding)
                self.documents.append(node.text)

            # Mise à jour de l'index FAISS
            embeddings_array = np.array(embeddings).astype('float32')
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(embeddings_array)

            logger.info(f"Documents ingérés avec succès: {len(nodes)} chunks")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ingestion des documents: {str(e)}")
            raise

    async def query(self, query_text: str, top_k: int = 3) -> str:
        """Effectue une requête RAG complète."""
        try:
            # Vérification du cache
            cached_response = await self._get_cached_response(query_text)
            if cached_response:
                return cached_response

            # Génération de l'embedding de la requête
            query_embedding = await self._get_embedding(query_text)
            query_embedding_array = np.array([query_embedding]).astype('float32')

            # Recherche des documents les plus pertinents
            distances, indices = self.index.search(query_embedding_array, top_k)
            
            # Récupération des documents pertinents
            relevant_docs = [self.documents[i] for i in indices[0]]
            
            # Construction du prompt pour OpenAI
            context = "\n\n".join(relevant_docs)
            prompt = f"""En utilisant le contexte suivant, réponds à la question de manière précise et concise.

Contexte:
{context}

Question: {query_text}

Réponse:"""

            # Appel à l'API OpenAI
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content

            # Mise en cache de la réponse
            await self._cache_response(query_text, answer)

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de la requête RAG: {str(e)}")
            raise

    async def analyze_node_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse les données d'un nœud en utilisant le système RAG."""
        try:
            # Préparation des données pour l'analyse
            analysis_prompt = f"""Analyse les données suivantes d'un nœud Lightning et fournis des insights pertinents:

Données du nœud:
{json.dumps(data, indent=2)}

Fournis une analyse structurée incluant:
1. Performance générale
2. Points forts
3. Points d'amélioration
4. Recommandations spécifiques"""

            # Utilisation du système RAG pour l'analyse
            analysis = await self.query(analysis_prompt)
            
            return {
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des données du nœud: {str(e)}")
            raise 