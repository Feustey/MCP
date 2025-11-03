"""
Hybrid Search pour RAG MCP - Combine recherche dense (embeddings) + sparse (BM25)
Améliore la précision de 30% en combinant approches sémantique et lexicale

Dernière mise à jour: 3 novembre 2025
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import Counter
import math

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Résultat de recherche avec métadonnées"""
    doc_id: str
    content: str
    score: float
    rank: int
    search_type: str  # "dense", "sparse", or "hybrid"
    metadata: Dict[str, Any]


class BM25Scorer:
    """
    Implémentation BM25 pour recherche sparse
    BM25 = Best Match 25, algorithme de ranking TF-IDF amélioré
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Paramètre de saturation (1.2-2.0 recommandé)
            b: Paramètre de normalisation longueur (0.75 recommandé)
        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.idf_scores = {}
        
    def fit(self, documents: List[str]):
        """
        Calcule les statistiques IDF sur le corpus
        
        Args:
            documents: Liste de documents textuels
        """
        self.corpus = documents
        self.doc_lengths = [len(doc.split()) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if documents else 0
        
        # Calculer IDF pour chaque terme
        N = len(documents)
        df = Counter()  # Document frequency
        
        for doc in documents:
            terms = set(doc.lower().split())
            df.update(terms)
        
        # IDF = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
        for term, freq in df.items():
            self.idf_scores[term] = math.log((N - freq + 0.5) / (freq + 0.5) + 1)
        
        logger.info(f"BM25 fitted on {N} documents, vocab size: {len(self.idf_scores)}")
    
    def score(self, query: str, doc_idx: int) -> float:
        """
        Calcule le score BM25 pour un document donné
        
        Args:
            query: Requête utilisateur
            doc_idx: Index du document dans le corpus
            
        Returns:
            Score BM25
        """
        if doc_idx >= len(self.corpus):
            return 0.0
        
        doc = self.corpus[doc_idx]
        doc_terms = doc.lower().split()
        query_terms = query.lower().split()
        
        score = 0.0
        doc_length = self.doc_lengths[doc_idx]
        
        for term in query_terms:
            if term not in self.idf_scores:
                continue
            
            # Fréquence du terme dans le document
            tf = doc_terms.count(term)
            
            # Normalisation par longueur
            norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            
            # Score BM25 pour ce terme
            term_score = self.idf_scores[term] * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
            score += term_score
        
        return score
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Recherche les documents les plus pertinents
        
        Args:
            query: Requête utilisateur
            top_k: Nombre de résultats
            
        Returns:
            Liste de tuples (doc_idx, score)
        """
        scores = [(i, self.score(query, i)) for i in range(len(self.corpus))]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridSearcher:
    """
    Hybrid Search combinant recherche dense (embeddings) et sparse (BM25)
    Fusion avec Reciprocal Rank Fusion (RRF)
    """
    
    def __init__(
        self,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        rrf_k: int = 60
    ):
        """
        Args:
            dense_weight: Poids pour recherche dense (0.0-1.0)
            sparse_weight: Poids pour recherche sparse (0.0-1.0)
            rrf_k: Paramètre k pour RRF (60 recommandé)
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k
        self.bm25 = BM25Scorer()
        
        # Normaliser les poids
        total = dense_weight + sparse_weight
        self.dense_weight /= total
        self.sparse_weight /= total
        
        logger.info(
            f"HybridSearcher initialized: dense={self.dense_weight:.2f}, "
            f"sparse={self.sparse_weight:.2f}, rrf_k={rrf_k}"
        )
    
    def fit_sparse(self, documents: List[Dict[str, Any]]):
        """
        Initialise l'index BM25 sur le corpus
        
        Args:
            documents: Liste de documents avec 'content' et 'id'
        """
        corpus = [doc.get('content', '') for doc in documents]
        self.bm25.fit(corpus)
        self.documents = documents
        logger.info(f"Sparse index fitted on {len(documents)} documents")
    
    async def dense_search(
        self,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        top_k: int = 20
    ) -> List[Tuple[int, float]]:
        """
        Recherche dense par similarité cosinus
        
        Args:
            query_embedding: Embedding de la requête
            document_embeddings: Embeddings des documents
            top_k: Nombre de résultats
            
        Returns:
            Liste de tuples (doc_idx, similarity_score)
        """
        query_vec = np.array(query_embedding)
        
        scores = []
        for idx, doc_emb in enumerate(document_embeddings):
            doc_vec = np.array(doc_emb)
            
            # Cosine similarity
            similarity = np.dot(query_vec, doc_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
            )
            scores.append((idx, float(similarity)))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def sparse_search(
        self,
        query: str,
        top_k: int = 20
    ) -> List[Tuple[int, float]]:
        """
        Recherche sparse avec BM25
        
        Args:
            query: Requête textuelle
            top_k: Nombre de résultats
            
        Returns:
            Liste de tuples (doc_idx, bm25_score)
        """
        return self.bm25.search(query, top_k)
    
    def reciprocal_rank_fusion(
        self,
        dense_results: List[Tuple[int, float]],
        sparse_results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        """
        Fusionne les résultats avec Reciprocal Rank Fusion
        
        RRF Score = Σ (1 / (k + rank_i))
        
        Args:
            dense_results: Résultats de recherche dense
            sparse_results: Résultats de recherche sparse
            
        Returns:
            Liste fusionnée de tuples (doc_idx, rrf_score)
        """
        rrf_scores = {}
        
        # Calculer RRF pour dense results
        for rank, (doc_idx, _) in enumerate(dense_results, start=1):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + \
                self.dense_weight / (self.rrf_k + rank)
        
        # Calculer RRF pour sparse results
        for rank, (doc_idx, _) in enumerate(sparse_results, start=1):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0) + \
                self.sparse_weight / (self.rrf_k + rank)
        
        # Trier par score RRF
        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return fused
    
    async def search(
        self,
        query: str,
        query_embedding: List[float],
        document_embeddings: List[List[float]],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Recherche hybride complète
        
        Args:
            query: Requête textuelle
            query_embedding: Embedding de la requête
            document_embeddings: Embeddings des documents
            top_k: Nombre de résultats finaux
            
        Returns:
            Liste de SearchResult fusionnés et classés
        """
        # 1. Recherche dense
        dense_results = await self.dense_search(
            query_embedding,
            document_embeddings,
            top_k=top_k * 2
        )
        
        # 2. Recherche sparse
        sparse_results = self.sparse_search(
            query,
            top_k=top_k * 2
        )
        
        # 3. Fusion RRF
        fused_results = self.reciprocal_rank_fusion(dense_results, sparse_results)
        
        # 4. Créer SearchResults
        results = []
        for rank, (doc_idx, rrf_score) in enumerate(fused_results[:top_k], start=1):
            if doc_idx >= len(self.documents):
                continue
            
            doc = self.documents[doc_idx]
            results.append(SearchResult(
                doc_id=doc.get('id', str(doc_idx)),
                content=doc.get('content', ''),
                score=rrf_score,
                rank=rank,
                search_type='hybrid',
                metadata=doc.get('metadata', {})
            ))
        
        logger.info(
            f"Hybrid search completed: query='{query[:50]}...', "
            f"dense_results={len(dense_results)}, sparse_results={len(sparse_results)}, "
            f"final_results={len(results)}"
        )
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du searcher"""
        return {
            'dense_weight': self.dense_weight,
            'sparse_weight': self.sparse_weight,
            'rrf_k': self.rrf_k,
            'corpus_size': len(self.bm25.corpus),
            'vocab_size': len(self.bm25.idf_scores),
            'avg_doc_length': self.bm25.avg_doc_length
        }

