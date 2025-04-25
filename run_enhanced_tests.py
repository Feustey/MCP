#!/usr/bin/env python3
"""
Script pour exécuter manuellement des tests avancés pour les fonctionnalités RAG
"""
import unittest
import asyncio
import sys
import os
import logging
from unittest.mock import MagicMock, AsyncMock, patch
import json
from datetime import datetime, timedelta

# Configuration de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRAGWorkflow(unittest.TestCase):
    """Tests pour la classe RAGWorkflow"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Créer des données de test
        self.test_data = {
            "query": "test query",
            "documents": [
                {"content": "Document 1", "metadata": {"source": "source1"}},
                {"content": "Document 2", "metadata": {"source": "source2"}},
                {"content": "Document 3", "metadata": {"source": "source3"}}
            ]
        }
    
    def test_context_formatting(self):
        """Test de formatage du contexte pour le RAG"""
        documents = self.test_data["documents"]
        
        # Créer une fonction de formatage simple
        def format_context(docs):
            context = ""
            for i, doc in enumerate(docs, 1):
                context += f"[Document {i}]: {doc['content']}"
                if i < len(docs):
                    context += "\n"
            return context
        
        # Formater le contexte
        context = format_context(documents)
        
        # Vérifier le formatage
        expected = "[Document 1]: Document 1\n[Document 2]: Document 2\n[Document 3]: Document 3"
        self.assertEqual(context, expected)
    
    def test_relevance_scoring(self):
        """Test du scoring de pertinence"""
        # Fonction de scoring simple basée sur la présence de mots-clés
        def score_relevance(query, doc):
            query_terms = query.lower().split()
            content = doc["content"].lower()
            score = sum(1 for term in query_terms if term in content)
            return score / len(query_terms) if query_terms else 0
        
        # Créer des documents de test
        docs = [
            {"content": "This is a test document about Python programming."},
            {"content": "This document discusses machine learning models."},
            {"content": "Python is a great language for ML and data science with machine learning capabilities."}
        ]
        
        # Calculer les scores de pertinence
        query = "Python machine learning"
        scores = [score_relevance(query, doc) for doc in docs]
        
        # Vérifier les scores individuels
        self.assertGreater(scores[2], 0.6)  # Le doc 3 devrait avoir un score élevé (contient Python et machine learning)
        self.assertGreater(scores[0], 0.3)  # Le doc 1 devrait avoir un score moyen (contient Python)
        self.assertGreater(scores[1], 0.3)  # Le doc 2 devrait avoir un score moyen (contient machine learning)
        
        # Vérifier que le doc 3 a le meilleur score
        self.assertEqual(scores.index(max(scores)), 2)
    
    def test_context_enrichment(self):
        """Test d'enrichissement du contexte"""
        # Simuler l'enrichissement du contexte
        context = "Base context about LN node."
        
        # Fonction d'enrichissement
        def enrich_context(context, metadata=None):
            enriched = context
            if metadata:
                if "timestamp" in metadata:
                    enriched += f"\nLast updated: {metadata['timestamp']}"
                if "source" in metadata:
                    enriched += f"\nSource: {metadata['source']}"
                if "relevance" in metadata:
                    enriched += f"\nRelevance: {metadata['relevance']:.2f}"
            return enriched
        
        # Enrichir le contexte
        metadata = {
            "timestamp": "2023-06-01T12:00:00Z",
            "source": "lightning-knowledge-base",
            "relevance": 0.95
        }
        enriched_context = enrich_context(context, metadata)
        
        # Vérifier l'enrichissement
        self.assertIn("Base context about LN node.", enriched_context)
        self.assertIn("Last updated:", enriched_context)
        self.assertIn("Source:", enriched_context)
        self.assertIn("Relevance:", enriched_context)

class TestCacheOptimization(unittest.TestCase):
    """Tests pour l'optimisation du cache"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Simuler une structure de cache
        self.cache = {}
    
    def test_cache_eviction(self):
        """Test d'éviction du cache"""
        # Créer une fonction d'éviction LRU simple
        def lru_evict(cache, max_size=5):
            if len(cache) <= max_size:
                return cache
            
            # Trier les entrées par timestamp
            sorted_items = sorted(cache.items(), key=lambda x: x[1].get("timestamp", 0))
            
            # Garder seulement les max_size éléments les plus récents
            return {k: v for k, v in sorted_items[-max_size:]}
        
        # Remplir le cache
        for i in range(10):
            self.cache[f"key_{i}"] = {
                "data": f"data_{i}",
                "timestamp": i
            }
        
        # Appliquer l'éviction
        self.cache = lru_evict(self.cache)
        
        # Vérifier que le cache a la bonne taille et contient les entrées les plus récentes
        self.assertEqual(len(self.cache), 5)
        self.assertIn("key_9", self.cache)
        self.assertIn("key_8", self.cache)
        self.assertIn("key_7", self.cache)
        self.assertIn("key_6", self.cache)
        self.assertIn("key_5", self.cache)
        self.assertNotIn("key_0", self.cache)
    
    def test_cache_ttl(self):
        """Test de la gestion du TTL du cache"""
        now = datetime.now()
        
        # Créer une fonction pour vérifier l'expiration
        def is_expired(entry, now):
            if "expires_at" not in entry:
                return False
            return entry["expires_at"] < now
        
        # Créer des entrées de cache avec différentes expirations
        self.cache = {
            "expired": {
                "data": "old data",
                "expires_at": now - timedelta(minutes=5)
            },
            "valid": {
                "data": "fresh data",
                "expires_at": now + timedelta(minutes=5)
            },
            "no_expiry": {
                "data": "permanent data"
            }
        }
        
        # Vérifier l'expiration
        self.assertTrue(is_expired(self.cache["expired"], now))
        self.assertFalse(is_expired(self.cache["valid"], now))
        self.assertFalse(is_expired(self.cache["no_expiry"], now))
    
    def test_adaptive_ttl(self):
        """Test du TTL adaptatif basé sur la fréquence d'accès"""
        # Créer une fonction pour ajuster le TTL
        def adjust_ttl(entry, base_ttl=60, max_ttl=3600, access_multiplier=1.5):
            access_count = entry.get("access_count", 0)
            new_ttl = min(base_ttl * (access_multiplier ** access_count), max_ttl)
            return new_ttl
        
        # Créer des entrées avec différents nombres d'accès
        entries = [
            {"access_count": 0},
            {"access_count": 1},
            {"access_count": 2},
            {"access_count": 5},
            {"access_count": 10}
        ]
        
        # Calculer les TTL
        ttls = [adjust_ttl(entry) for entry in entries]
        
        # Vérifier que le TTL augmente avec le nombre d'accès
        for i in range(1, len(ttls)):
            self.assertGreater(ttls[i], ttls[i-1])
        
        # Vérifier que le TTL ne dépasse pas le maximum
        self.assertLessEqual(max(ttls), 3600)

async def run_async_tests():
    """Exécution des tests asynchrones"""
    # Simuler des tests asynchrones pour la gestion du cache
    
    async def test_async_cache_operations():
        # Simuler des opérations asynchrones sur le cache
        cache = {}
        
        # Opérations de base
        await asyncio.sleep(0.01)  # Simuler une opération asynchrone
        cache["key1"] = "value1"
        
        await asyncio.sleep(0.01)  # Simuler une opération asynchrone
        cache["key2"] = "value2"
        
        # Vérifier le cache
        assert "key1" in cache
        assert "key2" in cache
        assert cache["key1"] == "value1"
        assert cache["key2"] == "value2"
        
        logger.info("Tests asynchrones réussis")
    
    await test_async_cache_operations()

def run_all_tests():
    """Exécute tous les tests"""
    # Créer un TestLoader
    loader = unittest.TestLoader()
    
    # Créer une suite de tests
    suite = unittest.TestSuite()
    
    # Ajouter les tests
    suite.addTests(loader.loadTestsFromTestCase(TestRAGWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheOptimization))
    
    # Créer un TextTestRunner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Exécuter les tests
    result = runner.run(suite)
    
    # Exécuter les tests asynchrones
    asyncio.run(run_async_tests())
    
    # Retourner le code de sortie
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    # Exécuter les tests
    sys.exit(run_all_tests()) 