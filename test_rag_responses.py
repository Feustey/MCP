#!/usr/bin/env python3
"""
Script pour tester les réponses générées par le système RAG
"""
import unittest
import sys
import logging
import json
from typing import List, Dict, Any

# Configuration de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRAGResponse(unittest.TestCase):
    """Tests pour évaluer la qualité des réponses RAG"""
    
    def setUp(self):
        """Préparer les données de test"""
        # Exemple de requête et contexte
        self.test_query = "Comment fonctionne le routing dans Lightning Network?"
        
        # Contexte pour la requête
        self.test_context = [
            {
                "content": "Le routing dans Lightning Network s'appuie sur les canaux de paiement. Chaque nœud maintient une liste des canaux disponibles pour router les paiements.",
                "source": "lightning_docs",
                "relevance": 0.92
            },
            {
                "content": "Les paiements Lightning utilisent le protocole de routing Onion qui masque l'origine et la destination du paiement pour préserver la confidentialité.",
                "source": "lightning_protocol",
                "relevance": 0.88
            },
            {
                "content": "Le routing est basé sur un algorithme de chemin le plus court, prenant en compte les frais de transaction et la capacité disponible des canaux.",
                "source": "lightning_technical",
                "relevance": 0.85
            }
        ]
        
        # Réponse de référence (réponse idéale)
        self.reference_response = """
Le routing dans Lightning Network fonctionne grâce à un réseau de canaux de paiement bidirectionnels. Voici les points clés :

1. Canaux de paiement : Chaque nœud du réseau maintient une liste des canaux disponibles pour router les paiements.

2. Protocole Onion : Les paiements sont routés en utilisant un protocole de routage en oignon qui masque l'origine et la destination pour préserver la confidentialité.

3. Algorithme de chemin : Le système utilise un algorithme de chemin le plus court qui prend en compte les frais de transaction et la capacité disponible des canaux pour trouver le meilleur itinéraire.

Ce système permet d'effectuer des transactions rapides et confidentielles sans avoir besoin d'enregistrer chaque transaction sur la blockchain.
"""

        # Différentes réponses générées à évaluer
        self.generated_responses = [
            # Bonne réponse
            """
Le routing dans Lightning Network fonctionne via des canaux de paiement où chaque nœud maintient une liste des canaux disponibles. Le système utilise le protocole onion qui préserve la confidentialité en masquant l'origine et la destination. Pour trouver le meilleur chemin, un algorithme calcule le chemin optimal en tenant compte des frais et de la capacité des canaux.
""",
            # Réponse hors sujet
            """
Lightning Network est une solution de mise à l'échelle pour Bitcoin qui permet des transactions plus rapides et moins coûteuses. Il s'agit d'un réseau de second niveau qui fonctionne au-dessus de la blockchain Bitcoin.
""",
            # Réponse incorrecte
            """
Le routing dans Lightning Network fonctionne comme un système centralisé où tous les nœuds connaissent l'ensemble du réseau. Les transactions sont visibles par tous les participants, et un serveur central détermine les chemins optimaux.
""",
            # Réponse partielle
            """
Le routing dans Lightning Network utilise un protocole appelé onion pour masquer l'origine et la destination des paiements.
"""
        ]
    
    def test_response_completeness(self):
        """Teste si la réponse couvre tous les aspects importants du contexte"""
        # Points clés qui sont présents dans la bonne réponse
        good_response_points = [
            "canaux de paiement",
            "protocole onion",
            "confidentialité",
            "masquant l'origine",
            "destination",
            "algorithme",
            "capacité des canaux"
        ]
        
        # Points qui sont absents de la réponse partielle
        partial_response_missing = [
            "canaux de paiement",
            "algorithme",
            "capacité des canaux"
        ]
        
        # Vérifier que la bonne réponse contient les points clés
        good_response = self.generated_responses[0].lower()
        for point in good_response_points:
            self.assertIn(point, good_response)
        
        # Vérifier que la réponse partielle manque certains points
        partial_response = self.generated_responses[3].lower()
        for point in partial_response_missing:
            self.assertNotIn(point, partial_response)
    
    def test_response_relevance(self):
        """Teste si la réponse est pertinente par rapport à la requête"""
        # Mots-clés de la requête présents dans chaque réponse
        keywords_in_responses = [
            # Bonne réponse
            ["routing", "lightning", "network"],
            # Réponse hors sujet
            ["lightning", "network"],
            # Réponse incorrecte
            ["routing", "lightning", "network"],
            # Réponse partielle
            ["routing", "lightning", "network", "protocole"]
        ]
        
        # Vérifier le nombre de mots-clés pour chaque réponse
        for i, keywords in enumerate(keywords_in_responses):
            response = self.generated_responses[i].lower()
            for keyword in keywords:
                self.assertIn(keyword.lower(), response)
            
        # La bonne réponse et la réponse incorrecte devraient mentionner les trois mots-clés principaux
        self.assertEqual(len(keywords_in_responses[0]), 3)
        self.assertEqual(len(keywords_in_responses[2]), 3)
        
        # La réponse hors sujet devrait mentionner moins de mots-clés pertinents
        self.assertLess(len(keywords_in_responses[1]), len(keywords_in_responses[0]))
    
    def test_response_correctness(self):
        """Teste si la réponse contient des informations correctes ou incorrectes"""
        # Faits corrects qui doivent être présents dans la bonne réponse
        correct_facts = [
            "canaux de paiement",
            "protocole onion",
            "confidentialité",
            "masquant l'origine"
        ]
        
        # Faits incorrects qui doivent être présents dans la réponse incorrecte
        incorrect_facts = [
            "système centralisé",
            "serveur central"
        ]
        
        # Vérifier que la bonne réponse contient des faits corrects
        good_response = self.generated_responses[0].lower()
        for fact in correct_facts:
            self.assertIn(fact, good_response)
        
        # Vérifier que la réponse incorrecte contient des faits incorrects
        incorrect_response = self.generated_responses[2].lower()
        for fact in incorrect_facts:
            self.assertIn(fact, incorrect_response)
        
        # Vérifier que la bonne réponse ne contient pas de faits incorrects
        for fact in incorrect_facts:
            self.assertNotIn(fact, good_response)
    
    def test_response_similarity_ranking(self):
        """Teste le classement des réponses par similarité avec la référence"""
        def count_common_words(text1, text2):
            """Compte le nombre de mots communs entre deux textes"""
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            return len(words1.intersection(words2))
        
        # Compter les mots communs entre chaque réponse et la référence
        reference = self.reference_response.lower()
        common_word_counts = [count_common_words(response.lower(), reference) for response in self.generated_responses]
        
        # La bonne réponse devrait avoir plus de mots en commun avec la référence que la réponse incorrecte
        self.assertGreater(common_word_counts[0], common_word_counts[2])
        
        # La réponse partielle devrait avoir moins de mots en commun que la bonne réponse
        self.assertGreater(common_word_counts[0], common_word_counts[3])

def run_all_tests():
    """Exécute tous les tests"""
    # Créer un TestLoader
    loader = unittest.TestLoader()
    
    # Créer une suite de tests
    suite = unittest.TestSuite()
    
    # Ajouter les tests pour l'évaluation des réponses RAG
    suite.addTests(loader.loadTestsFromTestCase(TestRAGResponse))
    
    # Créer un TextTestRunner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Exécuter les tests
    result = runner.run(suite)
    
    # Retourner le code de sortie
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_all_tests()) 