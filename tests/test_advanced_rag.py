#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from rag.query_expansion import QueryExpander, QueryRouter
from rag.rag import RAGWorkflow
from rag.hybrid_retriever import HybridRetriever

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Requêtes de test représentatives
TEST_QUERIES = [
    "Quelles sont les recommandations pour optimiser les frais du nœud Feustey?",
    "Quels sont les nœuds connectés à Feustey avec la plus grande capacité?",
    "Comment est calculé le score de centralité d'un nœud Lightning?",
    "Quels sont les avantages d'établir un canal avec ACINQ?",
    "Montre-moi les statistiques de Feustey"
]

async def test_query_expansion(rag_workflow):
    """Teste la fonctionnalité d'expansion de requête."""
    logger.info("=== TEST D'EXPANSION DE REQUÊTE ===")
    
    for query in TEST_QUERIES[:2]:  # On limite à 2 requêtes pour le test
        logger.info(f"Requête originale: {query}")
        
        # Obtenir l'expansion
        expanded = await rag_workflow.query_expander.expand_query(query)
        
        logger.info(f"Requête réécrite: {expanded['rewritten_query']}")
        logger.info(f"Sous-requêtes: {expanded['sub_queries']}")
        logger.info(f"Mots-clés: {expanded['keywords']}")
        logger.info("-" * 50)
    
    return True

async def test_query_routing(rag_workflow):
    """Teste la fonctionnalité de routage de requête."""
    logger.info("=== TEST DE ROUTAGE DE REQUÊTE ===")
    
    # Requêtes spéciales pour tester différents aspects du routage
    routing_queries = [
        "Montre-moi les statistiques du nœud 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "Quels sont les nœuds avec la plus grande capacité?",
        "Comment définir la politique de frais optimale?",
        "Montre-moi les canaux les plus récents"
    ]
    
    for query in routing_queries:
        logger.info(f"Requête: {query}")
        
        # Obtenir le routage
        routing = rag_workflow.query_router.analyze_query(query)
        
        logger.info(f"Stratégie recommandée: {routing['recommended_strategy']}")
        logger.info(f"Poids vectoriel: {routing['vector_weight']}")
        logger.info(f"Correspondances exactes: {routing['exact_matches']}")
        logger.info(f"Filtres: {routing['filters']}")
        logger.info("-" * 50)
    
    return True

async def test_hybrid_search(rag_workflow, query):
    """Teste la recherche hybride avec différentes configurations."""
    logger.info("=== TEST DE RECHERCHE HYBRIDE ===")
    
    # Tester différentes configurations
    configs = [
        {"use_hybrid": True, "use_expansion": True, "desc": "Recherche hybride avec expansion"},
        {"use_hybrid": True, "use_expansion": False, "desc": "Recherche hybride sans expansion"},
        {"use_hybrid": False, "use_expansion": False, "desc": "Recherche vectorielle pure"}
    ]
    
    results = {}
    
    for config in configs:
        logger.info(f"Configuration: {config['desc']}")
        
        start_time = datetime.now()
        
        response = await rag_workflow.query(
            query_text=query,
            top_k=5,
            use_hybrid=config["use_hybrid"],
            use_expansion=config["use_expansion"]
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Temps de traitement: {processing_time:.2f} secondes")
        logger.info(f"Réponse: {response[:150]}...")
        logger.info("-" * 50)
        
        results[config['desc']] = {
            "processing_time": processing_time,
            "response_length": len(response),
            "response": response[:200] + "..." if len(response) > 200 else response
        }
    
    return results

async def run_tests(data_dir, query=None):
    """Exécute tous les tests du système RAG avancé."""
    try:
        logger.info(f"Initialisation du système RAG avec les données de {data_dir}")
        
        # Créer une instance du RAGWorkflow
        rag = RAGWorkflow()
        rag.debug_mode = True
        
        # S'assurer que les données sont ingérées
        if not rag.documents:
            logger.info("Ingestion des documents...")
            result = await rag.ingest_documents(data_dir)
            logger.info(f"Documents ingérés: {result['documents_processed']} documents, "
                       f"{result['chunks_created']} chunks")
        
        # Tester l'expansion de requête
        logger.info("Test de l'expansion de requête...")
        await test_query_expansion(rag)
        
        # Tester le routage de requête
        logger.info("Test du routage de requête...")
        await test_query_routing(rag)
        
        # Tester la recherche hybride
        logger.info("Test de la recherche hybride...")
        query_to_test = query or TEST_QUERIES[0]
        results = await test_hybrid_search(rag, query_to_test)
        
        # Afficher les résultats comparatifs
        logger.info("=== RÉSULTATS COMPARATIFS ===")
        for desc, data in results.items():
            logger.info(f"{desc}:")
            logger.info(f"  - Temps: {data['processing_time']:.2f} secondes")
            logger.info(f"  - Longueur de réponse: {data['response_length']} caractères")
        
        logger.info("Tests terminés avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors des tests: {str(e)}")
        return False

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Test des fonctionnalités avancées du RAG")
    parser.add_argument('--data-dir', type=str, default='data/scrapping', 
                        help='Répertoire contenant les données à utiliser')
    parser.add_argument('--query', type=str, 
                        help='Requête spécifique à tester (optionnel)')
    args = parser.parse_args()
    
    # Vérifier que le répertoire existe
    if not os.path.isdir(args.data_dir):
        logger.error(f"Le répertoire {args.data_dir} n'existe pas")
        return 1
    
    # Exécuter les tests
    success = asyncio.run(run_tests(args.data_dir, args.query))
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 