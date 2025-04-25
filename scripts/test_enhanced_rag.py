#!/usr/bin/env python3
"""
Script de test pour le système RAG amélioré avec enrichissement du contexte.
Ce script permet de tester les fonctionnalités d'enrichissement du contexte
en réalisant diverses requêtes avec différentes contraintes.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import json

# Ajout du répertoire parent au path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.enhanced_rag import EnhancedRAGWorkflow
from src.redis_operations import RedisOperations

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/test_enhanced_rag.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_enhanced_rag")

# Requêtes de test avec différentes contraintes
TEST_QUERIES = [
    {
        "description": "Requête standard sans contrainte",
        "query": "Qu'est-ce que le réseau Lightning Network?",
        "params": {}
    },
    {
        "description": "Requête avec contrainte temporelle explicite",
        "query": "Quelles sont les tendances récentes des frais sur le réseau?",
        "params": {
            "time_range": (datetime.now() - timedelta(days=30), datetime.now())
        }
    },
    {
        "description": "Requête avec contrainte temporelle implicite",
        "query": "Quelles sont les performances du réseau pendant la dernière semaine?",
        "params": {}
    },
    {
        "description": "Requête avec filtrage par collection",
        "query": "Donnez-moi des exemples d'hypothèses validées sur les frais",
        "params": {
            "collection_filters": {"hypotheses": True, "metrics": False, "documents": False}
        }
    },
    {
        "description": "Requête combinant documents textuels et métriques",
        "query": "Comment optimiser la configuration des canaux Lightning?",
        "params": {
            "collection_filters": {"documents": True, "metrics": True, "hypotheses": True}
        }
    }
]

async def run_test_query(rag, query_info):
    """Exécute une requête de test et affiche les résultats"""
    description = query_info["description"]
    query = query_info["query"]
    params = query_info["params"]
    
    logger.info(f"===== TEST: {description} =====")
    logger.info(f"QUERY: {query}")
    
    try:
        start_time = datetime.now()
        response = await rag.query_enhanced(query, **params)
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"RESPONSE: {response}")
        logger.info(f"TIME: {duration:.2f} seconds")
        logger.info("="*50)
        
        return {
            "description": description,
            "query": query,
            "response": response,
            "duration": duration,
            "params": {k: str(v) for k, v in params.items()}  # Conversion pour JSON
        }
    except Exception as e:
        logger.error(f"ERREUR: {str(e)}")
        logger.info("="*50)
        return {
            "description": description,
            "query": query,
            "error": str(e),
            "params": {k: str(v) for k, v in params.items()}
        }

async def run_all_tests():
    """Exécute toutes les requêtes de test"""
    try:
        # Initialisation du Redis si disponible
        redis_ops = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            redis_ops = RedisOperations(redis_url)
        
        # Initialisation du RAG amélioré
        rag = EnhancedRAGWorkflow(redis_ops=redis_ops)
        await rag.initialize()
        
        # S'assurer que l'index unifié est construit
        if not os.path.exists("data/indexes/unified_index.meta"):
            logger.info("Construction de l'index unifié pour les tests...")
            await rag.refresh_unified_index()
        
        # Exécution des requêtes de test
        results = []
        for query_info in TEST_QUERIES:
            result = await run_test_query(rag, query_info)
            results.append(result)
        
        # Sauvegarde des résultats
        os.makedirs("test_results", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"test_results/enhanced_rag_test_{timestamp}.json", "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Tests terminés. Résultats sauvegardés dans test_results/enhanced_rag_test_{timestamp}.json")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des tests: {str(e)}")
    finally:
        # Fermeture des connexions
        await rag.close()

async def main():
    """Fonction principale"""
    logger.info("Démarrage des tests du RAG amélioré...")
    await run_all_tests()

if __name__ == "__main__":
    # Exécution des tests
    asyncio.run(main()) 