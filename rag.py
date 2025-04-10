import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging
import numpy as np
try:
    import faiss
except ImportError:
    import faiss_cpu as faiss
from openai import OpenAI
import redis.asyncio as redis
from tiktoken import encoding_for_model
import asyncio
from models import Document, QueryHistory, SystemStats
from mongo_operations import MongoOperations

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGWorkflow:
    def __init__(self):
        # Initialisation du client OpenAI
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Chargement du prompt système
        self.system_prompt = self._load_system_prompt()
        
        # Configuration du tokenizer
        self.tokenizer = encoding_for_model("gpt-3.5-turbo")
        
        # Configuration du text splitter
        self.chunk_size = 512
        self.chunk_overlap = 50
        
        # Initialisation de FAISS
        self.dimension = 1536  # Dimension des embeddings OpenAI
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        
        # Configuration Redis
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = None
        self.response_cache_ttl = 3600  # 1 heure

        # Initialisation MongoDB
        self.mongo_ops = MongoOperations()

    def _load_system_prompt(self) -> str:
        """Charge le prompt système depuis le fichier prompt-rag.md."""
        try:
            with open('prompt-rag.md', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extraire toutes les sections pertinentes
                sections = {
                    'context': re.search(r'## Contexte\n(.*?)\n\n', content, re.DOTALL),
                    'instructions': re.search(r'## Instructions pour l\'Analyse\n(.*?)\n\n', content, re.DOTALL),
                    'format': re.search(r'## Format de Réponse\n(.*?)\n\n', content, re.DOTALL)
                }
                
                prompt = """
                Tu es un assistant expert en analyse du réseau Lightning.
                
                CONTEXTE:
                {context}
                
                INSTRUCTIONS:
                {instructions}
                
                FORMAT DE RÉPONSE:
                {format}
                
                Assure-toi de suivre strictement ce format pour toutes les réponses.
                """.format(
                    context=sections['context'].group(1) if sections['context'] else "",
                    instructions=sections['instructions'].group(1) if sections['instructions'] else "",
                    format=sections['format'].group(1) if sections['format'] else ""
                )
                
                return prompt.strip()
        except Exception as e:
            logger.error(f"Erreur lors du chargement du prompt système: {str(e)}")
            return "Tu es un assistant expert qui fournit des réponses précises basées sur le contexte fourni."

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
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {str(e)}")
            raise

    def _split_text(self, text: str) -> List[str]:
        """Découpe le texte en chunks en utilisant tiktoken."""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
        return chunks

    async def ingest_documents(self, directory: str):
        """Ingère des documents dans le système RAG."""
        try:
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
                doc_chunks = self._split_text(doc)
                chunks.extend(doc_chunks)

            # Génération des embeddings et mise à jour de FAISS
            embeddings = []
            for chunk in chunks:
                embedding = await self._get_embedding(chunk)
                embeddings.append(embedding)
                self.documents.append(chunk)

                # Sauvegarde dans MongoDB
                document = Document(
                    content=chunk,
                    source=filename,
                    embedding=embedding,
                    metadata={
                        "chunk_index": len(embeddings) - 1,
                        "total_chunks": len(chunks)
                    }
                )
                await self.mongo_ops.save_document(document)

            # Mise à jour de l'index FAISS
            embeddings_array = np.array(embeddings).astype('float32')
            self.index = faiss.IndexFlatL2(self.dimension)
            self.index.add(embeddings_array)

            # Mise à jour des statistiques
            stats = await self.mongo_ops.get_system_stats() or SystemStats()
            stats.total_documents += len(chunks)
            stats.last_updated = datetime.now()
            await self.mongo_ops.update_system_stats(stats)

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

            # Génération de l'embedding de la requête
            query_embedding = await self._get_embedding(query_text)
            query_embedding_array = np.array([query_embedding]).astype('float32')

            # Recherche des documents les plus pertinents
            distances, indices = self.index.search(query_embedding_array, top_k)
            
            # Récupération des documents pertinents
            relevant_docs = [self.documents[i] for i in indices[0]]
            
            # Construction du prompt pour OpenAI avec structure détaillée
            context = "\n\n".join(relevant_docs)
            prompt = f"""En utilisant le contexte suivant, réponds à la question en suivant strictement le format spécifié.

Contexte:
{context}

Question: {query_text}

Format requis pour la réponse:

1. Résumé Exécutif
   - Points clés identifiés
   - Tendances principales
   - Recommandations prioritaires

2. Analyse Détaillée
   - Métriques quantitatives
   - Comparaisons historiques
   - Observations techniques

3. Insights et Actions
   - Patterns identifiés
   - Opportunités d'optimisation
   - Risques potentiels

Assure-toi que chaque section est clairement identifiée et contient les éléments requis.
Réponse:"""

            # Appel à l'API OpenAI avec le prompt système chargé
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000  # Augmenté pour permettre des réponses plus détaillées
            )

            answer = response.choices[0].message.content

            # Validation du format de la réponse
            if not self._validate_response_format(answer):
                logger.warning("La réponse ne suit pas le format requis, tentative de reformatage...")
                # Tentative de reformatage avec un prompt plus strict
                reformat_prompt = f"""Reformate la réponse suivante pour qu'elle suive exactement cette structure:

1. Résumé Exécutif
   - Points clés identifiés
   - Tendances principales
   - Recommandations prioritaires

2. Analyse Détaillée
   - Métriques quantitatives
   - Comparaisons historiques
   - Observations techniques

3. Insights et Actions
   - Patterns identifiés
   - Opportunités d'optimisation
   - Risques potentiels

Réponse à reformater:
{answer}

Réponse reformatée:"""

                reformat_response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un expert en formatage de réponses."},
                        {"role": "user", "content": reformat_prompt}
                    ],
                    temperature=0.3,  # Température plus basse pour un formatage plus strict
                    max_tokens=1000
                )
                answer = reformat_response.choices[0].message.content

            # Mise en cache de la réponse
            await self._cache_response(query_text, answer)

            # Mise à jour des statistiques
            stats = await self.mongo_ops.get_system_stats() or SystemStats()
            stats.total_queries += 1
            stats.cache_hits += 1 if cache_hit else 0
            stats.last_updated = datetime.now()
            await self.mongo_ops.update_system_stats(stats)

            # Log des métriques
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Requête traitée en {processing_time:.2f} secondes (cache hit: {cache_hit})")
            
            return answer

        except Exception as e:
            logger.error(f"Erreur lors de la requête RAG: {str(e)}")
            raise

    def _validate_response_format(self, response: str) -> bool:
        """
        Valide que la réponse suit le format requis.
        
        Args:
            response: La réponse à valider
            
        Returns:
            bool: True si le format est valide, False sinon
        """
        required_sections = [
            "Résumé Exécutif",
            "Analyse Détaillée",
            "Insights et Actions"
        ]
        
        for section in required_sections:
            if section not in response:
                logger.warning(f"Section manquante dans la réponse: {section}")
                return False
                
        # Vérification des sous-sections
        required_subsection_patterns = [
            r"Points clés.*?Tendances principales.*?Recommandations prioritaires",
            r"Métriques quantitatives.*?Comparaisons.*?Observations",
            r"Patterns identifiés.*?Opportunités.*?Risques"
        ]
        
        for pattern in required_subsection_patterns:
            if not re.search(pattern, response, re.DOTALL | re.IGNORECASE):
                logger.warning(f"Structure de sous-sections incorrecte pour le pattern: {pattern}")
                return False
                
        return True 

    async def update_prompt(self):
        """
        Met à jour le prompt système avec les dernières connaissances et statistiques.
        """
        try:
            # Récupérer les dernières statistiques
            stats = await self.mongo_ops.get_system_stats()
            
            # Récupérer l'historique des requêtes récentes
            recent_queries = await self.mongo_ops.get_recent_query_history(limit=10)
            
            # Construire un résumé des tendances
            trends = []
            if recent_queries:
                # Analyser les patterns dans les requêtes récentes
                common_topics = self._analyze_query_patterns(recent_queries)
                trends.append(f"Topics fréquents: {', '.join(common_topics)}")
            
            # Mettre à jour le prompt avec les nouvelles informations
            current_prompt = self._load_system_prompt()
            updated_prompt = f"""{current_prompt}

INFORMATIONS DE PERFORMANCE:
- Nombre total de requêtes: {stats.total_queries}
- Taux de hit du cache: {(stats.cache_hits / stats.total_queries * 100):.1f}%
- Dernière mise à jour: {stats.last_updated}

TENDANCES RÉCENTES:
{chr(10).join(trends)}

Assure-toi d'adapter tes réponses en fonction de ces tendances et statistiques.
"""
            
            self.system_prompt = updated_prompt
            logger.info("Prompt système mis à jour avec succès")
            
            # Sauvegarder la version du prompt
            await self.mongo_ops.save_prompt_version(updated_prompt)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prompt: {str(e)}")
            
    def _analyze_query_patterns(self, queries: List[QueryHistory]) -> List[str]:
        """
        Analyse les patterns dans les requêtes récentes.
        
        Args:
            queries: Liste des requêtes récentes
            
        Returns:
            Liste des topics fréquents
        """
        # Extraction des mots-clés des requêtes
        keywords = []
        for query in queries:
            # Utiliser des regex pour extraire les topics
            topics = re.findall(r'(?:analyse|performance|optimisation|recommandation|risque)s?', 
                              query.query.lower())
            keywords.extend(topics)
            
        # Compter les occurrences
        from collections import Counter
        topic_counts = Counter(keywords)
        
        # Retourner les 3 topics les plus fréquents
        return [topic for topic, _ in topic_counts.most_common(3)] 