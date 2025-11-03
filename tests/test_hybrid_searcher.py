"""
Tests unitaires pour Hybrid Searcher
"""

import pytest
import numpy as np
from src.hybrid_searcher import HybridSearcher, BM25Scorer, SearchResult


class TestBM25Scorer:
    """Tests pour BM25Scorer"""
    
    def test_bm25_initialization(self):
        """Test initialisation BM25"""
        scorer = BM25Scorer(k1=1.5, b=0.75)
        assert scorer.k1 == 1.5
        assert scorer.b == 0.75
        assert len(scorer.corpus) == 0
    
    def test_bm25_fit(self):
        """Test fit sur corpus"""
        documents = [
            "Lightning Network fees optimization",
            "Channel balance management HTLC",
            "Routing node centrality betweenness"
        ]
        
        scorer = BM25Scorer()
        scorer.fit(documents)
        
        assert len(scorer.corpus) == 3
        assert scorer.avg_doc_length > 0
        assert len(scorer.idf_scores) > 0
    
    def test_bm25_score(self):
        """Test calcul score BM25"""
        documents = [
            "Lightning Network fees optimization",
            "Channel balance management",
            "Routing node centrality"
        ]
        
        scorer = BM25Scorer()
        scorer.fit(documents)
        
        # Score pour requête pertinente
        score = scorer.score("Lightning fees", 0)
        assert score > 0
        
        # Score pour requête non pertinente
        score_irrelevant = scorer.score("Bitcoin blockchain", 0)
        assert score > score_irrelevant
    
    def test_bm25_search(self):
        """Test recherche BM25"""
        documents = [
            "Lightning Network fees optimization strategy",
            "Channel balance management and liquidity",
            "Routing node centrality betweenness calculation",
            "HTLC timeout and failure handling"
        ]
        
        scorer = BM25Scorer()
        scorer.fit(documents)
        
        results = scorer.search("Lightning fees optimization", top_k=2)
        
        assert len(results) == 2
        assert results[0][0] == 0  # Premier doc le plus pertinent
        assert results[0][1] > results[1][1]  # Score décroissant


class TestHybridSearcher:
    """Tests pour HybridSearcher"""
    
    @pytest.fixture
    def sample_documents(self):
        """Documents de test"""
        return [
            {
                'id': 'doc1',
                'content': 'Lightning Network fees and routing optimization',
                'metadata': {'source': 'technical'}
            },
            {
                'id': 'doc2',
                'content': 'Channel balance management for Lightning nodes',
                'metadata': {'source': 'guide'}
            },
            {
                'id': 'doc3',
                'content': 'Network centrality metrics betweenness closeness',
                'metadata': {'source': 'analysis'}
            }
        ]
    
    @pytest.fixture
    def sample_embeddings(self):
        """Embeddings de test"""
        np.random.seed(42)
        return [
            np.random.rand(768).tolist() for _ in range(3)
        ]
    
    def test_hybrid_initialization(self):
        """Test initialisation HybridSearcher"""
        searcher = HybridSearcher(
            dense_weight=0.7,
            sparse_weight=0.3,
            rrf_k=60
        )
        
        assert searcher.dense_weight == 0.7
        assert searcher.sparse_weight == 0.3
        assert searcher.rrf_k == 60
    
    def test_weight_normalization(self):
        """Test normalisation des poids"""
        searcher = HybridSearcher(
            dense_weight=7,
            sparse_weight=3,
            rrf_k=60
        )
        
        # Poids doivent être normalisés à 0.7 et 0.3
        assert abs(searcher.dense_weight - 0.7) < 0.01
        assert abs(searcher.sparse_weight - 0.3) < 0.01
    
    def test_fit_sparse(self, sample_documents):
        """Test fit de l'index sparse"""
        searcher = HybridSearcher()
        searcher.fit_sparse(sample_documents)
        
        assert len(searcher.bm25.corpus) == 3
        assert len(searcher.documents) == 3
    
    @pytest.mark.asyncio
    async def test_dense_search(self, sample_embeddings):
        """Test recherche dense"""
        searcher = HybridSearcher()
        
        query_emb = sample_embeddings[0]
        results = await searcher.dense_search(
            query_embedding=query_emb,
            document_embeddings=sample_embeddings,
            top_k=2
        )
        
        assert len(results) == 2
        assert all(0 <= score <= 1 for _, score in results)
    
    def test_sparse_search(self, sample_documents):
        """Test recherche sparse"""
        searcher = HybridSearcher()
        searcher.fit_sparse(sample_documents)
        
        results = searcher.sparse_search("Lightning fees", top_k=2)
        
        assert len(results) == 2
        assert results[0][1] >= results[1][1]  # Scores décroissants
    
    def test_reciprocal_rank_fusion(self):
        """Test fusion RRF"""
        searcher = HybridSearcher()
        
        dense_results = [(0, 0.9), (1, 0.8), (2, 0.7)]
        sparse_results = [(1, 100), (0, 80), (2, 60)]
        
        fused = searcher.reciprocal_rank_fusion(dense_results, sparse_results)
        
        assert len(fused) == 3
        # Vérifier que les scores sont fusionnés
        doc_ids = [doc_id for doc_id, _ in fused]
        assert len(set(doc_ids)) == 3
    
    @pytest.mark.asyncio
    async def test_hybrid_search_complete(self, sample_documents, sample_embeddings):
        """Test recherche hybride complète"""
        searcher = HybridSearcher(
            dense_weight=0.7,
            sparse_weight=0.3
        )
        searcher.fit_sparse(sample_documents)
        
        query = "Lightning Network optimization"
        query_emb = sample_embeddings[0]
        
        results = await searcher.search(
            query=query,
            query_embedding=query_emb,
            document_embeddings=sample_embeddings,
            top_k=2
        )
        
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.search_type == 'hybrid' for r in results)
        assert results[0].rank == 1
        assert results[1].rank == 2
    
    def test_get_stats(self, sample_documents):
        """Test statistiques"""
        searcher = HybridSearcher()
        searcher.fit_sparse(sample_documents)
        
        stats = searcher.get_stats()
        
        assert 'dense_weight' in stats
        assert 'sparse_weight' in stats
        assert 'corpus_size' in stats
        assert stats['corpus_size'] == 3

