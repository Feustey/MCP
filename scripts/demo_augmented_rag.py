#!/usr/bin/env python3
"""
Script de démonstration du système RAG Augmenté.
Ce script montre l'utilisation du workflow RAG augmenté avec différents types de requêtes.
"""

import os
import sys
# Ajouter le répertoire parent au sys.path pour trouver le module src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import logging
import time
import json
from datetime import datetime
from argparse import ArgumentParser

from src.augmented_rag import AugmentedRAGWorkflow
from src.redis_operations import RedisOperations
from src.mongo_operations import MongoOperations

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Requêtes de démonstration pour différents types de requêtes
DEMO_QUERIES = {
    "technique": [
        "Comment fonctionne le mécanisme de routage dans Lightning Network?",
        "Quelle est l'architecture du réseau Lightning?",
        "Comment se déroule l'ouverture d'un canal Lightning?"
    ],
    "historique": [
        "Comment ont évolué les frais de transaction pendant le dernier mois?",
        "Quelle est la tendance des performances du réseau depuis la semaine dernière?",
        "Montre-moi l'historique des métriques pour le nœud 023d220a55d9bc55f8b16b55c241d7154248a612cd3083e783242a68d1995f2602"
    ],
    "prédictive": [
        "Quelle stratégie de frais pourrait optimiser les revenus du réseau?",
        "Quelles recommandations as-tu pour améliorer la liquidité des canaux?",
        "Suggère des configurations optimales basées sur les hypothèses validées"
    ]
}

async def setup_workflow(redis_url=None, mongo_url=None):
    """
    Configure et initialise le workflow RAG augmenté.
    
    Args:
        redis_url: URL de connexion Redis (optionnel)
        mongo_url: URL de connexion MongoDB (optionnel)
        
    Returns:
        Instance initialisée du workflow
    """
    # Initialisation des connexions
    redis_ops = None
    if redis_url:
        redis_ops = RedisOperations(redis_url)
        logger.info("Connexion Redis initialisée")
    
    mongo_ops = None
    if mongo_url:
        mongo_ops = MongoOperations(mongo_url)
        logger.info("Connexion MongoDB initialisée")
    
    # Création du workflow
    workflow = AugmentedRAGWorkflow(
        model_name="gpt-4",
        embedding_model="all-MiniLM-L6-v2",
        redis_ops=redis_ops,
        mongo_ops=mongo_ops
    )
    
    # Initialisation
    await workflow.initialize()
    logger.info("Workflow RAG augmenté initialisé avec succès")
    
    return workflow

async def run_demo_query(workflow, query, query_type=None, save_results=False):
    """
    Exécute une requête de démonstration et affiche les résultats.
    
    Args:
        workflow: Instance du workflow RAG augmenté
        query: Texte de la requête
        query_type: Type attendu de la requête (pour validation)
        save_results: Sauvegarder les résultats dans un fichier JSON
        
    Returns:
        Résultat de la requête
    """
    logger.info(f"Exécution de la requête: '{query}'")
    start_time = time.time()
    
    # Exécution de la requête
    result = await workflow.query_augmented(
        query=query,
        top_k=5,
        dynamic_weighting=True,
        use_adaptive_prompt=True
    )
    
    # Calcul du temps d'exécution
    execution_time = time.time() - start_time
    result["metadata"]["execution_time"] = execution_time
    
    # Affichage des résultats
    detected_type = result.get("query_type", "unknown")
    print("\n" + "="*80)
    print(f"REQUÊTE: {query}")
    print(f"TYPE DÉTECTÉ: {detected_type}" + 
          (f" (attendu: {query_type})" if query_type else ""))
    print(f"TEMPS D'EXÉCUTION: {execution_time:.2f} secondes")
    print("-"*80)
    print(f"RÉPONSE:\n{result['response']}")
    print("-"*80)
    
    # Affichage des métadonnées importantes
    source_weights = result.get("metadata", {}).get("source_weights", {})
    print(f"POIDS DES SOURCES: {json.dumps(source_weights, indent=2)}")
    
    # Nombre de documents par source
    sources_count = {}
    for doc in result.get("context_documents", []):
        source = doc.get("metadata", {}).get("source", "unknown")
        sources_count[source] = sources_count.get(source, 0) + 1
    
    print(f"DOCUMENTS PAR SOURCE: {json.dumps(sources_count, indent=2)}")
    print("="*80 + "\n")
    
    # Sauvegarde des résultats si demandé
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"demo_results_{detected_type}_{timestamp}.json"
        
        # Simplifier les documents pour la sérialisation JSON
        simplified_result = result.copy()
        simplified_result["context_documents"] = [
            {
                "content": doc.get("content", ""),
                "source": doc.get("metadata", {}).get("source", "unknown"),
                "type": doc.get("metadata", {}).get("type", "unknown"),
                "score": doc.get("final_score", 0)
            }
            for doc in result.get("context_documents", [])
        ]
        
        with open(filename, "w") as f:
            json.dump(simplified_result, f, indent=2)
        
        logger.info(f"Résultats sauvegardés dans {filename}")
    
    return result

async def run_demo(redis_url=None, mongo_url=None, query_type=None, save_results=False):
    """
    Exécute la démonstration complète ou pour un type de requête spécifique.
    
    Args:
        redis_url: URL de connexion Redis (optionnel)
        mongo_url: URL de connexion MongoDB (optionnel)
        query_type: Type de requête à démontrer (technique, historique, prédictive ou all)
        save_results: Sauvegarder les résultats dans des fichiers JSON
    """
    # Initialisation du workflow
    workflow = await setup_workflow(redis_url, mongo_url)
    
    # Sélection des requêtes à exécuter
    if query_type and query_type.lower() != "all":
        query_types = [query_type.lower()]
    else:
        query_types = DEMO_QUERIES.keys()
    
    # Exécution des requêtes
    for current_type in query_types:
        print(f"\n\n{'='*40} REQUÊTES DE TYPE {current_type.upper()} {'='*40}\n")
        for query in DEMO_QUERIES.get(current_type, []):
            await run_demo_query(workflow, query, current_type, save_results)
    
    # Affichage des poids finaux des sources
    print("\n\nPOIDS FINAUX DES SOURCES APRÈS APPRENTISSAGE:")
    print(json.dumps(workflow.context_manager.source_weights, indent=2))

async def run_custom_query(query, redis_url=None, mongo_url=None, save_results=False):
    """
    Exécute une requête personnalisée.
    
    Args:
        query: Texte de la requête
        redis_url: URL de connexion Redis (optionnel)
        mongo_url: URL de connexion MongoDB (optionnel)
        save_results: Sauvegarder les résultats dans un fichier JSON
    """
    # Initialisation du workflow
    workflow = await setup_workflow(redis_url, mongo_url)
    
    # Exécution de la requête
    await run_demo_query(workflow, query, save_results=save_results)

def main():
    """Fonction principale avec parsing des arguments"""
    parser = ArgumentParser(description="Démo du système RAG Augmenté")
    parser.add_argument("--redis-url", help="URL de connexion Redis")
    parser.add_argument("--mongo-url", help="URL de connexion MongoDB")
    parser.add_argument("--query-type", choices=["technique", "historique", "prédictive", "all"],
                      default="all", help="Type de requête à démontrer")
    parser.add_argument("--custom-query", help="Requête personnalisée à exécuter")
    parser.add_argument("--save-results", action="store_true", 
                      help="Sauvegarder les résultats dans des fichiers JSON")
    
    args = parser.parse_args()
    
    if args.custom_query:
        asyncio.run(run_custom_query(
            args.custom_query, 
            args.redis_url, 
            args.mongo_url,
            args.save_results
        ))
    else:
        asyncio.run(run_demo(
            args.redis_url, 
            args.mongo_url, 
            args.query_type,
            args.save_results
        ))

if __name__ == "__main__":
    main() 