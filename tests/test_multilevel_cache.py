#!/usr/bin/env python3
import asyncio
import argparse
import logging
import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from rag.multilevel_cache import MultiLevelCache

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Données de test
TEST_DATA = {
    "embeddings": {
        "query1": [0.1, 0.2, 0.3, 0.4],
        "query2": [0.5, 0.6, 0.7, 0.8],
        "long_document_text": [0.1] * 100  # Liste plus longue pour tester la sérialisation
    },
    "retrieval_results": {
        "query1": [
            {"id": 1, "content": "Document 1 content", "score": 0.95},
            {"id": 2, "content": "Document 2 content", "score": 0.85}
        ],
        "query2": [
            {"id": 3, "content": "Document 3 content", "score": 0.75},
            {"id": 4, "content": "Document 4 content", "score": 0.65}
        ]
    },
    "generation_results": {
        "query1": "Voici une réponse générée pour la requête 1.",
        "query2": "Voici une réponse générée pour la requête 2.",
        "query3": "Voici une réponse générée pour la requête 3."
    },
    "query_expansions": {
        "comment optimiser frais": {
            "rewritten_query": "comment optimiser les frais du nœud lightning",
            "sub_queries": ["optimisation frais lightning", "réduire coûts canaux lightning"],
            "keywords": ["frais", "optimisation", "lightning", "nœud", "canal"]
        },
        "qu'est-ce que lightning": {
            "rewritten_query": "qu'est-ce que le réseau Lightning Network",
            "sub_queries": ["principes lightning network", "fonctionnement canaux lightning"],
            "keywords": ["lightning", "network", "bitcoin", "layer 2", "canaux"]
        }
    }
}

async def test_basic_operations():
    """Teste les opérations de base du cache (get, set, invalidate)."""
    logger.info("=== TEST DES OPÉRATIONS DE BASE DU CACHE ===")
    
    # Créer le cache
    cache = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Test de l'opération SET
    logger.info("Test de l'opération SET...")
    for data_type, items in TEST_DATA.items():
        for key, value in items.items():
            success = await cache.set(key, value, data_type)
            logger.info(f"SET {data_type}:{key} - {'Success' if success else 'Failed'}")
    
    # Test de l'opération GET
    logger.info("\nTest de l'opération GET...")
    for data_type, items in TEST_DATA.items():
        for key, expected_value in items.items():
            value = await cache.get(key, data_type)
            match = value == expected_value
            logger.info(f"GET {data_type}:{key} - {'Match' if match else 'Mismatch'}")
    
    # Test de l'opération INVALIDATE
    logger.info("\nTest de l'opération INVALIDATE...")
    
    # Invalider une clé spécifique
    count = await cache.invalidate("query1", "generation_results")
    logger.info(f"INVALIDATE generation_results:query1 - {count} entries invalidated")
    
    # Vérifier que la clé a bien été invalidée
    value = await cache.get("query1", "generation_results")
    logger.info(f"After invalidation, GET generation_results:query1 - {'Found' if value else 'Not found (expected)'}")
    
    # Récupérer les statistiques
    stats = cache.get_stats()
    logger.info(f"\nStatistiques du cache:\n{json.dumps(stats, indent=2)}")
    
    # Fermer le cache
    await cache.close()
    
    return True

async def test_cache_persistence():
    """Teste la persistance des données entre différentes instances du cache."""
    logger.info("=== TEST DE LA PERSISTANCE DU CACHE ===")
    
    # Première instance de cache
    logger.info("Création de la première instance de cache...")
    cache1 = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Stocker des données
    test_key = f"test_persistence_{int(time.time())}"
    test_value = {"timestamp": datetime.now().isoformat(), "data": "Test persistence"}
    
    logger.info(f"Stockage de données: {test_key}")
    await cache1.set(test_key, test_value, "generation_results")
    
    # Fermer la première instance
    await cache1.close()
    logger.info("Première instance de cache fermée.")
    
    # Deuxième instance de cache
    logger.info("Création de la seconde instance de cache...")
    cache2 = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Tenter de récupérer les données
    logger.info(f"Tentative de récupération des données: {test_key}")
    value = await cache2.get(test_key, "generation_results")
    
    if value == test_value:
        logger.info("Persistance vérifiée! Les données ont été correctement récupérées.")
    else:
        logger.warning(f"Échec de la persistance. Valeur attendue: {test_value}, Valeur reçue: {value}")
    
    # Nettoyer
    await cache2.invalidate(test_key, "generation_results")
    await cache2.close()
    
    return value == test_value

async def test_cache_performance():
    """Teste les performances du cache (latence, hit rate)."""
    logger.info("=== TEST DES PERFORMANCES DU CACHE ===")
    
    # Créer le cache
    cache = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Données de test pour les performances
    test_data = {}
    num_items = 1000
    
    # Créer des données de test
    logger.info(f"Création de {num_items} éléments de test...")
    for i in range(num_items):
        test_data[f"perf_key_{i}"] = {
            "id": i,
            "data": f"Performance test data for item {i}",
            "timestamp": datetime.now().isoformat()
        }
    
    # 1. Test d'écriture
    logger.info("Test de performance d'écriture...")
    start_time = time.time()
    
    for key, value in test_data.items():
        await cache.set(key, value, "retrieval_results")
    
    write_time = time.time() - start_time
    logger.info(f"Temps d'écriture pour {num_items} éléments: {write_time:.4f} secondes")
    logger.info(f"Moyenne par élément: {(write_time * 1000 / num_items):.4f} ms")
    
    # 2. Test de lecture (premier accès - lecture depuis Redis)
    logger.info("\nTest de performance de lecture (premier accès)...")
    start_time = time.time()
    
    read_count = 0
    for key in list(test_data.keys())[:100]:  # Lire seulement les 100 premiers
        value = await cache.get(key, "retrieval_results")
        if value:
            read_count += 1
    
    first_read_time = time.time() - start_time
    logger.info(f"Temps de lecture pour 100 éléments (premier accès): {first_read_time:.4f} secondes")
    logger.info(f"Moyenne par élément: {(first_read_time * 1000 / 100):.4f} ms")
    
    # 3. Test de lecture (deuxième accès - lecture depuis le cache mémoire)
    logger.info("\nTest de performance de lecture (deuxième accès - cache mémoire)...")
    start_time = time.time()
    
    read_count = 0
    for key in list(test_data.keys())[:100]:  # Mêmes 100 éléments
        value = await cache.get(key, "retrieval_results")
        if value:
            read_count += 1
    
    second_read_time = time.time() - start_time
    logger.info(f"Temps de lecture pour 100 éléments (cache mémoire): {second_read_time:.4f} secondes")
    logger.info(f"Moyenne par élément: {(second_read_time * 1000 / 100):.4f} ms")
    
    # 4. Test d'invalidation
    logger.info("\nTest de performance d'invalidation...")
    start_time = time.time()
    
    count = await cache.invalidate("perf_key", "retrieval_results")
    
    invalidate_time = time.time() - start_time
    logger.info(f"Temps d'invalidation pour {count} éléments: {invalidate_time:.4f} secondes")
    
    # Statistiques
    stats = cache.get_stats()
    logger.info(f"\nStatistiques du cache après les tests de performance:\n{json.dumps(stats, indent=2)}")
    
    # Nettoyer
    await cache.clear_all("retrieval_results")
    await cache.close()
    
    return True

async def test_cache_capacity():
    """Teste la gestion de la capacité du cache mémoire."""
    logger.info("=== TEST DE LA GESTION DE LA CAPACITÉ DU CACHE ===")
    
    # Créer le cache
    cache = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Récupérer la capacité du cache pour les embeddings
    capacity = cache.memory_capacity.get("embeddings", 500)
    logger.info(f"Capacité maximale pour 'embeddings': {capacity}")
    
    # Générer plus d'éléments que la capacité
    num_items = capacity + 50
    logger.info(f"Ajout de {num_items} éléments (dépassant la capacité)...")
    
    # Ajouter les éléments
    for i in range(num_items):
        key = f"capacity_test_{i}"
        value = [0.1, 0.2, 0.3, 0.4]  # Embedding factice
        await cache.set(key, value, "embeddings")
    
    # Vérifier que le cache a limité le nombre d'éléments
    stats = cache.get_stats()
    embeddings_count = stats["memory_by_type"]["embeddings"]["count"]
    
    logger.info(f"Nombre d'éléments 'embeddings' dans le cache mémoire: {embeddings_count}")
    logger.info(f"Respect de la capacité: {'Oui' if embeddings_count <= capacity else 'Non'}")
    
    # Nettoyer
    await cache.clear_all("embeddings")
    await cache.close()
    
    return embeddings_count <= capacity

async def analyze_cache_performance():
    """Analyse comparative des performances du cache multi-niveaux avec graphiques."""
    logger.info("=== ANALYSE COMPARATIVE DES PERFORMANCES DU CACHE ===")
    
    # Créer le cache
    cache = MultiLevelCache(redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'))
    
    # Configuration des tests
    test_sizes = [10, 50, 100, 500, 1000]
    data_types = ["embeddings", "retrieval_results", "generation_results"]
    
    # Structures pour stocker les résultats
    memory_read_times = {data_type: [] for data_type in data_types}
    redis_read_times = {data_type: [] for data_type in data_types}
    write_times = {data_type: [] for data_type in data_types}
    
    # Exécuter les tests pour chaque taille et type de données
    for data_type in data_types:
        logger.info(f"\nAnalyse pour le type de données: {data_type}")
        
        for size in test_sizes:
            logger.info(f"Test avec {size} éléments...")
            
            # Générer des données de test
            test_data = {}
            for i in range(size):
                if data_type == "embeddings":
                    test_data[f"bench_key_{i}"] = [0.1, 0.2, 0.3, 0.4, 0.5] * 10
                elif data_type == "retrieval_results":
                    test_data[f"bench_key_{i}"] = [{"id": i, "score": 0.9, "content": "Test content " * 10}]
                else:  # generation_results
                    test_data[f"bench_key_{i}"] = "Réponse générée pour le test " * 5
            
            # 1. Test d'écriture
            start_time = time.time()
            for key, value in test_data.items():
                await cache.set(key, value, data_type)
            write_time = (time.time() - start_time) * 1000 / size  # ms par élément
            write_times[data_type].append(write_time)
            
            # 2. Test de lecture depuis Redis (premier accès)
            await cache.clear_all(data_type)  # Vider le cache mémoire mais garder Redis
            
            start_time = time.time()
            for key in test_data.keys():
                await cache.get(key, data_type)
            redis_read_time = (time.time() - start_time) * 1000 / size  # ms par élément
            redis_read_times[data_type].append(redis_read_time)
            
            # 3. Test de lecture depuis le cache mémoire (deuxième accès)
            start_time = time.time()
            for key in test_data.keys():
                await cache.get(key, data_type)
            memory_read_time = (time.time() - start_time) * 1000 / size  # ms par élément
            memory_read_times[data_type].append(memory_read_time)
            
            logger.info(f"Résultats pour {size} éléments:")
            logger.info(f"  Écriture: {write_time:.2f} ms/élément")
            logger.info(f"  Lecture (Redis): {redis_read_time:.2f} ms/élément")
            logger.info(f"  Lecture (Mémoire): {memory_read_time:.2f} ms/élément")
            logger.info(f"  Gain de performance: {(redis_read_time/memory_read_time):.1f}x")
    
    # Nettoyer les données
    for data_type in data_types:
        await cache.clear_all(data_type)
    
    # Fermer le cache
    await cache.close()
    
    # Générer des graphiques
    plt.figure(figsize=(15, 10))
    
    # 1. Graphique des temps d'écriture
    plt.subplot(2, 2, 1)
    for data_type in data_types:
        plt.plot(test_sizes, write_times[data_type], marker='o', label=data_type)
    plt.title("Temps d'écriture par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 2. Graphique des temps de lecture depuis Redis
    plt.subplot(2, 2, 2)
    for data_type in data_types:
        plt.plot(test_sizes, redis_read_times[data_type], marker='o', label=data_type)
    plt.title("Temps de lecture depuis Redis par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 3. Graphique des temps de lecture depuis la mémoire
    plt.subplot(2, 2, 3)
    for data_type in data_types:
        plt.plot(test_sizes, memory_read_times[data_type], marker='o', label=data_type)
    plt.title("Temps de lecture depuis la mémoire par élément")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Temps (ms)")
    plt.legend()
    plt.grid(True)
    
    # 4. Graphique comparatif des gains de performance
    plt.subplot(2, 2, 4)
    for data_type in data_types:
        gains = [r/m if m > 0 else 0 for r, m in zip(redis_read_times[data_type], memory_read_times[data_type])]
        plt.plot(test_sizes, gains, marker='o', label=data_type)
    plt.title("Gain de performance mémoire vs Redis")
    plt.xlabel("Nombre d'éléments")
    plt.ylabel("Facteur d'accélération (x)")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Sauvegarder le graphique
    output_dir = "cache_analysis"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f"{output_dir}/cache_performance_{timestamp}.png")
    logger.info(f"Graphique d'analyse enregistré: cache_performance_{timestamp}.png")
    
    # Enregistrer les données brutes en JSON
    results = {
        "write_times": write_times,
        "redis_read_times": redis_read_times,
        "memory_read_times": memory_read_times,
        "test_sizes": test_sizes,
        "timestamp": timestamp
    }
    
    with open(f"{output_dir}/cache_performance_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Données d'analyse enregistrées: cache_performance_{timestamp}.json")
    
    return True

def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Test du cache multi-niveaux")
    parser.add_argument('--test', choices=['basic', 'persistence', 'performance', 'capacity', 'analyze', 'all'], 
                        default='all', help='Type de test à exécuter')
    parser.add_argument('--performance', action='store_true', 
                        help='Afficher les informations de performance détaillées')
    args = parser.parse_args()
    
    # Exécuter les tests appropriés
    asyncio.run(run_tests(args.test, args.performance))
    
    return 0

async def run_tests(test_type: str, performance: bool = False):
    """Exécute les tests spécifiés."""
    if test_type == 'basic' or test_type == 'all':
        await test_basic_operations()
    
    if test_type == 'persistence' or test_type == 'all':
        await test_cache_persistence()
    
    if test_type == 'performance' or test_type == 'all':
        await test_cache_performance()
    
    if test_type == 'capacity' or test_type == 'all':
        await test_cache_capacity()
        
    if test_type == 'analyze' or performance:
        await analyze_cache_performance()
    
    logger.info("Tous les tests ont été exécutés avec succès!")

if __name__ == "__main__":
    exit(main()) 