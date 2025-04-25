import unittest
import asyncio
import datetime
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import re

# Ajouter le répertoire parent au chemin d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.context_enrichment import EnhancedContextManager
from src.enhanced_rag import EnhancedRAGWorkflow


class TestAugmentedRetrieval(unittest.TestCase):
    """Tests pour les fonctionnalités de récupération augmentée"""
    
    def setUp(self):
        """Configure l'environnement de test"""
        self.enhanced_context = EnhancedContextManager(
            embedding_model="test-embedding-model",
            vector_db_conn=MagicMock(),
            direct_db_conn=MagicMock()
        )
        
        # Mocking des méthodes de recherche
        self.enhanced_context._vector_search = MagicMock(return_value=[])
        self.enhanced_context._direct_db_retrieval = MagicMock(return_value=[])
        
        # Préparation des documents de test
        self.test_documents = [
            {
                "_id": "doc1",
                "content": "Guide technique d'architecture du système Lightning Network",
                "metadata": {
                    "type": "document",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(days=5)
                }
            },
            {
                "_id": "doc2",
                "content": "Évolution des métriques de performance du réseau sur les 3 derniers mois",
                "metadata": {
                    "type": "metrics",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(days=15)
                }
            },
            {
                "_id": "doc3",
                "content": "Hypothèse sur l'impact des frais de transaction sur l'adoption future",
                "metadata": {
                    "type": "hypothesis",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(days=30)
                }
            }
        ]
    
    def test_extract_constraints_from_query(self):
        """Test l'extraction des contraintes à partir de requêtes"""
        # Test d'extraction de contrainte temporelle
        query1 = "Montre-moi les performances du réseau de la semaine dernière"
        constraints1 = self.enhanced_context._extract_constraints_from_query(query1)
        self.assertIn("time_range", constraints1)
        self.assertIsInstance(constraints1["time_range"], tuple)
        self.assertEqual(len(constraints1["time_range"]), 2)
        
        # Test d'extraction d'ID de nœud
        query2 = "Quelles sont les performances du nœud 023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602"
        constraints2 = self.enhanced_context._extract_constraints_from_query(query2)
        self.assertIn("node_ids", constraints2)
        self.assertEqual(constraints2["node_ids"][0], "023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602")
        
        # Test d'extraction de type de collection
        query3 = "Montre-moi les dernières métriques de performance du réseau"
        constraints3 = self.enhanced_context._extract_constraints_from_query(query3)
        self.assertIn("collection_filters", constraints3)
        self.assertTrue(constraints3["collection_filters"].get("metrics"))
    
    def test_determine_query_type(self):
        """Test la détermination du type de requête"""
        # Test de requête technique
        tech_query = "Comment fonctionne le mécanisme de routage dans Lightning Network?"
        self.assertEqual(self.enhanced_context._determine_query_type(tech_query), "technical")
        
        # Test de requête historique
        hist_query = "Quelle a été l'évolution du nombre de canaux au cours des derniers mois?"
        self.assertEqual(self.enhanced_context._determine_query_type(hist_query), "historical")
        
        # Test de requête prédictive
        pred_query = "Quelle est ta recommandation pour améliorer la liquidité du réseau?"
        self.assertEqual(self.enhanced_context._determine_query_type(pred_query), "predictive")
        
        # Test de requête sans mots-clés spécifiques (par défaut: technique)
        default_query = "Qu'est-ce que le Lightning Network?"
        self.assertEqual(self.enhanced_context._determine_query_type(default_query), "technical")
    
    def test_hybrid_retrieval(self):
        """Test la récupération hybride avec et sans contraintes"""
        # Configuration des mocks pour retourner les résultats
        vector_results = [self.test_documents[0]]
        direct_results = [self.test_documents[2]]
        
        self.enhanced_context._vector_search.return_value = vector_results
        self.enhanced_context._direct_db_retrieval.return_value = direct_results
        
        # Test sans contraintes (seulement vector search)
        query = "Lightning Network architecture"
        constraints = {}
        results = run_async_test(self.enhanced_context._hybrid_retrieval(query, constraints))
        self.assertEqual(len(results), 1)
        self.enhanced_context._vector_search.assert_called_once()
        self.enhanced_context._direct_db_retrieval.assert_not_called()
        
        # Réinitialisation des mocks
        self.enhanced_context._vector_search.reset_mock()
        self.enhanced_context._direct_db_retrieval.reset_mock()
        
        # Test avec contraintes (vector search + direct retrieval)
        constraints = {"node_ids": ["023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602"]}
        results = run_async_test(self.enhanced_context._hybrid_retrieval(query, constraints))
        self.assertEqual(len(results), 2)
        self.enhanced_context._vector_search.assert_called_once()
        self.enhanced_context._direct_db_retrieval.assert_called_once()
    
    def test_source_weighting(self):
        """Test la pondération des sources selon le type de requête"""
        # Préparation des résultats à pondérer
        results = [
            {
                "_id": "doc1",
                "_score": 0.8,
                "metadata": {"type": "document", "timestamp": datetime.datetime.now()}
            },
            {
                "_id": "doc2",
                "_score": 0.8,
                "metadata": {"type": "metrics", "timestamp": datetime.datetime.now()}
            },
            {
                "_id": "doc3",
                "_score": 0.8,
                "metadata": {"type": "hypothesis", "timestamp": datetime.datetime.now()}
            }
        ]
        
        # Test pour une requête technique
        weighted_tech = self.enhanced_context._apply_dynamic_weighting(
            results, "technical", {}
        )
        # Les documents techniques devraient avoir le score le plus élevé
        self.assertTrue(
            weighted_tech[0]["_score"] > weighted_tech[1]["_score"] and 
            weighted_tech[0]["_score"] > weighted_tech[2]["_score"]
        )
        
        # Test pour une requête historique
        weighted_hist = self.enhanced_context._apply_dynamic_weighting(
            results, "historical", {}
        )
        # Les métriques devraient avoir le score le plus élevé
        self.assertTrue(
            weighted_hist[1]["_score"] > weighted_hist[0]["_score"] and 
            weighted_hist[1]["_score"] > weighted_hist[2]["_score"]
        )
        
        # Test pour une requête prédictive
        weighted_pred = self.enhanced_context._apply_dynamic_weighting(
            results, "predictive", {}
        )
        # Les hypothèses devraient avoir le score le plus élevé
        self.assertTrue(
            weighted_pred[2]["_score"] > weighted_pred[0]["_score"] and 
            weighted_pred[2]["_score"] > weighted_pred[1]["_score"]
        )
    
    def test_full_retrieval_workflow(self):
        """Test le flux complet de récupération augmentée"""
        # Configuration des mocks pour ce test
        async def mock_vector_search(query, constraints):
            return [self.test_documents[0], self.test_documents[1]]
        
        async def mock_direct_retrieval(constraints):
            if "node_ids" in constraints:
                return [self.test_documents[2]]
            return []
        
        self.enhanced_context._vector_search = mock_vector_search
        self.enhanced_context._direct_db_retrieval = mock_direct_retrieval
        
        # Requête complexe avec un node ID et un indice temporel
        query = "Montre-moi l'évolution des performances du nœud 023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602 durant le mois dernier"
        
        # Exécution du flux complet
        results = run_async_test(self.enhanced_context.retrieve_enhanced_context(query, max_results=10))
        
        # Vérification des résultats
        self.assertEqual(len(results), 3)  # Tous les documents de test
        
        # Vérification que les résultats sont triés par score
        self.assertTrue(all(results[i]["_score"] >= results[i+1]["_score"] for i in range(len(results)-1)))
        
        # Avec cette requête, les documents de métriques devraient être privilégiés
        # car c'est une requête de type historique
        self.assertEqual(results[0]["metadata"]["type"], "metrics")
    
    def test_direct_db_retrieval(self):
        """Test la récupération directe en base de données avec différentes contraintes"""
        # Mock pour la connexion à la base de données
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.get_collection.return_value = mock_collection
        
        # Configuration du mock pour retourner des résultats
        mock_collection.find.return_value = AsyncMock(
            __aiter__=AsyncMock(return_value=self.test_documents)
        )
        
        # Remplacer la connexion DB pour ce test
        self.enhanced_context.direct_db_conn = mock_db
        
        # Test avec contrainte de temps
        time_now = datetime.datetime.now()
        time_week_ago = time_now - datetime.timedelta(days=7)
        constraints = {
            "time_range": (time_week_ago, time_now)
        }
        
        # Exécuter la récupération
        results = run_async_test(self.enhanced_context._direct_db_retrieval(constraints))
        
        # Vérifier l'appel à la base de données
        mock_db.get_collection.assert_called()
        mock_collection.find.assert_called()
        
        # Vérifier que la requête contient bien le filtre de temps
        call_args = mock_collection.find.call_args[0][0]
        self.assertIn("metadata.timestamp", call_args)
        
        # Test avec ID de nœud
        constraints = {
            "node_ids": ["023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602"]
        }
        
        # Réinitialiser les mocks
        mock_db.reset_mock()
        mock_collection.reset_mock()
        mock_collection.find.return_value = AsyncMock(
            __aiter__=AsyncMock(return_value=[self.test_documents[0]])
        )
        
        # Exécuter la récupération
        results = run_async_test(self.enhanced_context._direct_db_retrieval(constraints))
        
        # Vérifier que la requête contient bien le filtre de node_id
        call_args = mock_collection.find.call_args[0][0]
        self.assertIn("node_ids", call_args)
    
    def test_deduplication_in_hybrid_retrieval(self):
        """Test la déduplication des résultats dans la récupération hybride"""
        # Créer des documents avec les mêmes _id mais des scores différents
        doc1_vector = {
            "_id": "duplicate_doc",
            "_score": 0.8,
            "content": "Document from vector search",
            "metadata": {"type": "document"}
        }
        
        doc1_direct = {
            "_id": "duplicate_doc",
            "_score": 0.6,
            "content": "Same document from direct retrieval",
            "metadata": {"type": "document"}
        }
        
        doc2 = {
            "_id": "unique_doc",
            "_score": 0.7,
            "content": "Unique document",
            "metadata": {"type": "metrics"}
        }
        
        # Configurer les mocks pour retourner ces documents
        async def mock_vector_search(query, constraints):
            return [doc1_vector, doc2]
        
        async def mock_direct_retrieval(constraints):
            return [doc1_direct]
        
        self.enhanced_context._vector_search = mock_vector_search
        self.enhanced_context._direct_db_retrieval = mock_direct_retrieval
        
        # Exécuter la récupération hybride
        results = run_async_test(self.enhanced_context._hybrid_retrieval("test query", {"some_constraint": True}))
        
        # Vérifier qu'il n'y a pas de doublons et que le document avec le score le plus élevé est conservé
        self.assertEqual(len(results), 2)  # Au lieu de 3 sans déduplication
        
        # Vérifier que le document avec le meilleur score a été conservé
        duplicate_doc = next(doc for doc in results if doc["_id"] == "duplicate_doc")
        self.assertEqual(duplicate_doc["_score"], 0.8)  # Le score du document venant de vector_search

def run_async_test(coroutine):
    """Permet d'exécuter une coroutine dans un test unitaire"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)

if __name__ == "__main__":
    unittest.main() 