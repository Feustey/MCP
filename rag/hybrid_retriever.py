import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from rank_bm25 import BM25Okapi
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Système de récupération hybride qui combine recherche vectorielle (sémantique) 
    et recherche BM25 (lexicale) pour améliorer la précision.
    """
    
    def __init__(
        self, 
        documents: List[str],
        document_embeddings: Optional[np.ndarray] = None,
        embedding_model: Optional[Any] = None,
        vector_weight: float = 0.7
    ):
        """
        Initialise le système de récupération hybride.
        
        Args:
            documents: Liste des documents textuels
            document_embeddings: Embeddings précalculés pour les documents (optionnel)
            embedding_model: Modèle d'embedding pour convertir les textes en vecteurs
            vector_weight: Poids de la recherche vectorielle (0-1) par rapport à BM25
        """
        self.documents = documents
        self.document_embeddings = document_embeddings
        self.embedding_model = embedding_model
        self.vector_weight = max(0.0, min(1.0, vector_weight))  # Contraindre entre 0 et 1
        
        # Dimension par défaut des embeddings (sera mise à jour si document_embeddings est fourni)
        self.dimension = 1536
        
        # Initialiser BM25
        self._init_bm25()
        
        # Initialiser l'index vectoriel si embeddings fournis
        if document_embeddings is not None:
            self._init_vector_index(document_embeddings)
            
        # Initialisation TF-IDF (alternative/complément à BM25)
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
            
        logger.info(f"HybridRetriever initialisé avec {len(documents)} documents")
        logger.info(f"Poids vectoriel: {self.vector_weight}, BM25: {1-self.vector_weight}")
    
    def _init_bm25(self):
        """Initialise le modèle BM25 à partir des documents."""
        # Tokenize les documents pour BM25
        self.tokenized_docs = [doc.split() for doc in self.documents]
        # Créer l'index BM25
        self.bm25 = BM25Okapi(self.tokenized_docs)
        logger.info("Index BM25 initialisé avec succès")
        
    def _init_vector_index(self, embeddings: np.ndarray):
        """Initialise l'index vectoriel (FAISS) avec les embeddings fournis."""
        embeddings = embeddings.astype('float32')
        self.dimension = embeddings.shape[1]
        
        # Créer et ajouter à l'index
        self.vector_index = faiss.IndexFlatIP(self.dimension)  # Similarité cosinus (produit scalaire)
        self.vector_index.add(embeddings)
        
        logger.info(f"Index vectoriel FAISS initialisé avec dimension {self.dimension}")
    
    async def _get_query_embedding(self, query: str) -> np.ndarray:
        """Obtient l'embedding d'une requête."""
        if self.embedding_model is None:
            raise ValueError("embedding_model doit être fourni pour calculer l'embedding de la requête")
        
        try:
            embedding = self.embedding_model.get_text_embedding(query)
            return np.array(embedding, dtype='float32').reshape(1, -1)
        except Exception as e:
            logger.error(f"Erreur lors du calcul de l'embedding: {str(e)}")
            raise
    
    def _search_bm25(self, query: str, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """Effectue une recherche lexicale avec BM25."""
        query_tokens = query.split()
        scores = self.bm25.get_scores(query_tokens)
        
        # Trouver les top-k indices par score
        top_indices = np.argsort(scores)[::-1][:top_k]
        top_scores = [scores[i] for i in top_indices]
        
        # Normaliser les scores entre 0 et 1
        if max(top_scores) > 0:
            top_scores = [s / max(top_scores) for s in top_scores]
        
        return top_indices.tolist(), top_scores
    
    def _search_tfidf(self, query: str, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """Effectue une recherche avec TF-IDF comme alternative à BM25."""
        try:
            query_vec = self.tfidf_vectorizer.transform([query])
            scores = (self.tfidf_matrix @ query_vec.T).toarray().flatten()
            
            # Trouver les top-k indices par score
            top_indices = np.argsort(scores)[::-1][:top_k]
            top_scores = [scores[i] for i in top_indices]
            
            # Normaliser les scores entre 0 et 1
            if max(top_scores) > 0:
                top_scores = [s / max(top_scores) for s in top_scores]
            
            return top_indices.tolist(), top_scores
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche TF-IDF: {str(e)}, retour aux résultats BM25")
            return self._search_bm25(query, top_k)
    
    async def _search_vector(self, query_embedding: np.ndarray, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """Effectue une recherche sémantique avec l'index vectoriel."""
        if self.vector_index is None:
            raise ValueError("L'index vectoriel n'a pas été initialisé")
        
        # Recherche dans l'index vectoriel
        scores, indices = self.vector_index.search(query_embedding, top_k)
        
        # Normaliser les scores entre 0 et 1
        # Les scores sont déjà des similarités cosinus, normalement entre -1 et 1
        # Les convertir pour qu'ils soient entre 0 et 1
        normalized_scores = [(s[0] + 1) / 2 for s in scores]
        
        return indices[0].tolist(), normalized_scores
    
    async def retrieve(self, query: str, top_k: int = 10, rerank: bool = True) -> List[Dict[str, Any]]:
        """
        Effectue une récupération hybride combinant recherche vectorielle et lexicale.
        
        Args:
            query: Requête textuelle
            top_k: Nombre de documents à récupérer
            rerank: Si True, effectue un re-ranking des résultats combinés
            
        Returns:
            Liste de dictionnaires contenant les documents, scores et métadonnées
        """
        # 1. Recherche lexicale avec BM25
        lexical_indices, lexical_scores = self._search_bm25(query, top_k * 2)
        
        # 2. Recherche avec TF-IDF comme signal supplémentaire
        tfidf_indices, tfidf_scores = self._search_tfidf(query, top_k * 2)
        
        # 3. Recherche vectorielle (si embeddings disponibles)
        vector_indices, vector_scores = [], []
        
        if self.vector_index is not None:
            query_embedding = await self._get_query_embedding(query)
            vector_indices, vector_scores = await self._search_vector(query_embedding, top_k * 2)
        
        # 4. Combinaison des résultats avec un système de score pondéré
        combined_scores = {}
        
        # Ajouter scores BM25 (lexical)
        lexical_weight = (1 - self.vector_weight) * 0.6  # 60% du poids lexical à BM25
        for idx, score in zip(lexical_indices, lexical_scores):
            combined_scores[idx] = combined_scores.get(idx, 0) + score * lexical_weight
            
        # Ajouter scores TF-IDF
        tfidf_weight = (1 - self.vector_weight) * 0.4  # 40% du poids lexical à TF-IDF
        for idx, score in zip(tfidf_indices, tfidf_scores):
            combined_scores[idx] = combined_scores.get(idx, 0) + score * tfidf_weight
        
        # Ajouter scores vectoriels (sémantique)
        if vector_indices:
            for idx, score in zip(vector_indices, vector_scores):
                combined_scores[idx] = combined_scores.get(idx, 0) + score * self.vector_weight
                
        # 5. Trier par score combiné et prendre les top_k
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # 6. Formatter les résultats
        results = []
        for doc_idx, score in sorted_results:
            results.append({
                "id": doc_idx,
                "content": self.documents[doc_idx],
                "score": score,
                "lexical_score": lexical_scores[lexical_indices.index(doc_idx)] if doc_idx in lexical_indices else 0,
                "tfidf_score": tfidf_scores[tfidf_indices.index(doc_idx)] if doc_idx in tfidf_indices else 0,
                "vector_score": vector_scores[vector_indices.index(doc_idx)] if doc_idx in vector_indices else 0,
            })
        
        return results
        
    async def retrieve_with_filter(self, query: str, filter_func, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Effectue une récupération avec filtre personnalisé sur les résultats.
        
        Args:
            query: Requête textuelle
            filter_func: Fonction de filtrage prenant un document et retournant un booléen
            top_k: Nombre de documents à récupérer
            
        Returns:
            Liste de dictionnaires contenant les documents, scores et métadonnées
        """
        # Récupérer un plus grand nombre de résultats pour pouvoir filtrer
        results = await self.retrieve(query, top_k * 3)
        
        # Appliquer le filtre
        filtered_results = [r for r in results if filter_func(r["content"])]
        
        # Retourner les top_k résultats filtrés
        return filtered_results[:top_k] 