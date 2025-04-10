import asyncio
import time
import pytest
import statistics
from typing import List, Dict, Any
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import json

# Importer les composants RAG
from src.rag_workflow import RAGWorkflow
from src.rag_config import RAGConfig
from src.rag_monitoring import RAGMonitoring
from src.rag_data_provider import RAGDataProvider
from src.cache_manager import CacheManager

# Configuration des tests
TEST_CONFIG = {
    "concurrent_users": [1, 5, 10, 20, 50],  # Nombre d'utilisateurs simultanés
    "requests_per_user": 10,                 # Nombre de requêtes par utilisateur
    "request_delay": 0.1,                    # Délai entre les requêtes (secondes)
    "cache_enabled": True,                    # Activer le cache pour les tests
    "output_dir": "tests/load_tests/results",  # Répertoire de sortie pour les résultats
}

# Exemple de requêtes de test
TEST_QUERIES = [
    "Comment optimiser mon nœud Lightning?",
    "Quelles sont les meilleures pratiques pour la gestion des canaux Lightning?",
    "Comment améliorer la liquidité de mon nœud?",
    "Quels sont les risques des nœuds Lightning mal configurés?",
    "Comment surveiller efficacement mon nœud Lightning?",
    "Quel est l'impact des frais sur la rentabilité d'un nœud?",
    "Comment calculer le ROI d'un nœud Lightning?",
    "Quelles sont les meilleures stratégies d'ouverture de canaux?",
    "Comment gérer efficacement la distribution de liquidité?",
    "Quels outils utiliser pour analyser les performances d'un nœud?",
]

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("tests/load_tests/load_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("load_test")

class LoadTestResult:
    """Classe pour stocker et analyser les résultats des tests de charge"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count: int = 0
        self.error_count: int = 0
        self.cache_hits: int = 0
        self.start_time: float = 0
        self.end_time: float = 0
        self.config: Dict[str, Any] = {}
        
    def add_response_time(self, time: float, is_cache_hit: bool = False):
        """Ajoute un temps de réponse aux résultats"""
        self.response_times.append(time)
        self.success_count += 1
        if is_cache_hit:
            self.cache_hits += 1
            
    def add_error(self):
        """Incrémente le compteur d'erreurs"""
        self.error_count += 1
        
    def get_statistics(self) -> Dict[str, Any]:
        """Calcule les statistiques des temps de réponse"""
        if not self.response_times:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
                "std_dev": 0
            }
            
        return {
            "min": min(self.response_times),
            "max": max(self.response_times),
            "avg": statistics.mean(self.response_times),
            "p50": statistics.median(self.response_times),
            "p90": np.percentile(self.response_times, 90),
            "p95": np.percentile(self.response_times, 95),
            "p99": np.percentile(self.response_times, 99),
            "std_dev": statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0
        }
        
    def get_summary(self) -> Dict[str, Any]:
        """Génère un résumé des résultats du test"""
        total_requests = self.success_count + self.error_count
        duration = self.end_time - self.start_time if self.end_time > 0 else 0
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "cache_hits": self.cache_hits,
            "cache_hit_ratio": self.cache_hits / self.success_count if self.success_count > 0 else 0,
            "success_ratio": self.success_count / total_requests if total_requests > 0 else 0,
            "total_duration": duration,
            "requests_per_second": total_requests / duration if duration > 0 else 0,
            "statistics": self.get_statistics(),
            "test_config": self.config
        }
        
    def generate_charts(self, output_dir: str, test_name: str):
        """Génère des graphiques basés sur les résultats"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.response_times:
            logger.warning("Aucune donnée disponible pour générer des graphiques")
            return
            
        # Graphique de la distribution des temps de réponse
        plt.figure(figsize=(10, 6))
        plt.hist(self.response_times, bins=20, alpha=0.7, color='blue')
        plt.title('Distribution des temps de réponse')
        plt.xlabel('Temps (secondes)')
        plt.ylabel('Nombre de requêtes')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_dir}/{test_name}_response_distribution.png")
        
        # Graphique du temps de réponse en fonction du temps
        plt.figure(figsize=(10, 6))
        plt.plot(range(len(self.response_times)), self.response_times, marker='o', linestyle='-', alpha=0.5)
        plt.title('Temps de réponse par requête')
        plt.xlabel('Numéro de requête')
        plt.ylabel('Temps (secondes)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_dir}/{test_name}_response_timeline.png")
        
        # Enregistrement des données brutes
        with open(f"{output_dir}/{test_name}_raw_data.json", 'w') as f:
            json.dump({
                "response_times": self.response_times,
                "summary": self.get_summary()
            }, f, indent=2)
        
        logger.info(f"Graphiques et données brutes enregistrés dans {output_dir}")


async def run_user_simulation(
    user_id: int,
    workflow: RAGWorkflow,
    queries: List[str],
    delay: float,
    result: LoadTestResult
) -> None:
    """Simule un utilisateur faisant des requêtes au système RAG"""
    for i, query in enumerate(queries):
        try:
            # Mesurer le temps de réponse
            start_time = time.time()
            
            # Vérifier si c'est un cache hit avant d'appeler la fonction
            cache_key = f"response:{hash(query)}"
            cache_result = await workflow.cache_manager.get(cache_key)
            is_cache_hit = cache_result is not None
            
            # Exécuter la requête
            response = await workflow.query(query)
            
            # Enregistrer le temps de réponse
            response_time = time.time() - start_time
            result.add_response_time(response_time, is_cache_hit)
            
            logger.debug(f"User {user_id}, Query {i+1}: {response_time:.3f}s (Cache hit: {is_cache_hit})")
            
        except Exception as e:
            logger.error(f"User {user_id}, Query {i+1} failed: {str(e)}")
            result.add_error()
            
        # Pause entre les requêtes
        await asyncio.sleep(delay)


async def run_load_test(
    concurrent_users: int,
    requests_per_user: int,
    request_delay: float,
    cache_enabled: bool
) -> LoadTestResult:
    """Exécute un test de charge avec le nombre spécifié d'utilisateurs concurrents"""
    result = LoadTestResult()
    result.config = {
        "concurrent_users": concurrent_users,
        "requests_per_user": requests_per_user,
        "request_delay": request_delay,
        "cache_enabled": cache_enabled
    }
    
    # Initialiser les composants RAG
    config = RAGConfig()
    cache_manager = await CacheManager().initialize()
    monitoring = RAGMonitoring()
    data_provider = RAGDataProvider()
    
    # Créer une instance du workflow RAG
    workflow = RAGWorkflow(config)
    workflow.cache_manager = cache_manager
    workflow.monitoring = monitoring
    workflow.data_provider = data_provider
    
    # Désactiver le cache si nécessaire
    if not cache_enabled:
        # Méthode de désactivation du cache
        workflow.cache_manager.cache = {}
        workflow.cache_manager.timestamps = {}
    
    # Distribuer les requêtes aux utilisateurs
    user_queries = []
    for user_id in range(concurrent_users):
        # Chaque utilisateur obtient un ensemble de requêtes aléatoires
        user_query_set = [
            TEST_QUERIES[i % len(TEST_QUERIES)]
            for i in range(user_id, user_id + requests_per_user)
        ]
        user_queries.append(user_query_set)
    
    # Démarrer le chronométrage
    result.start_time = time.time()
    
    # Exécuter les simulations d'utilisateurs en parallèle
    tasks = [
        run_user_simulation(
            user_id,
            workflow,
            user_queries[user_id],
            request_delay,
            result
        )
        for user_id in range(concurrent_users)
    ]
    
    await asyncio.gather(*tasks)
    
    # Terminer le chronométrage
    result.end_time = time.time()
    
    return result


@pytest.mark.asyncio
async def test_rag_performance_scaling():
    """Test de mise à l'échelle des performances du système RAG"""
    logger.info(f"Démarrage des tests de charge avec {len(TEST_CONFIG['concurrent_users'])} configurations")
    
    os.makedirs(TEST_CONFIG["output_dir"], exist_ok=True)
    summary_file = f"{TEST_CONFIG['output_dir']}/summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    all_results = []
    
    for user_count in TEST_CONFIG["concurrent_users"]:
        logger.info(f"Test avec {user_count} utilisateurs concurrents")
        
        # Exécuter le test de charge
        result = await run_load_test(
            concurrent_users=user_count,
            requests_per_user=TEST_CONFIG["requests_per_user"],
            request_delay=TEST_CONFIG["request_delay"],
            cache_enabled=TEST_CONFIG["cache_enabled"]
        )
        
        # Générer les graphiques
        test_name = f"users_{user_count}"
        result.generate_charts(TEST_CONFIG["output_dir"], test_name)
        
        # Obtenir le résumé
        summary = result.get_summary()
        all_results.append(summary)
        
        logger.info(f"Résultats pour {user_count} utilisateurs:")
        logger.info(f"  Temps moyen: {summary['statistics']['avg']:.3f}s")
        logger.info(f"  Requêtes par seconde: {summary['requests_per_second']:.2f}")
        logger.info(f"  Taux de succès: {summary['success_ratio']*100:.1f}%")
        logger.info(f"  Taux de cache hit: {summary['cache_hit_ratio']*100:.1f}%")
    
    # Enregistrer le résumé global
    with open(summary_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Générer un graphique comparatif des performances
    plt.figure(figsize=(12, 8))
    
    user_counts = [r["test_config"]["concurrent_users"] for r in all_results]
    avg_times = [r["statistics"]["avg"] for r in all_results]
    throughputs = [r["requests_per_second"] for r in all_results]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # Graphique des temps de réponse moyens
    ax1.plot(user_counts, avg_times, marker='o', linestyle='-', linewidth=2)
    ax1.set_title('Temps de réponse moyen par nombre d\'utilisateurs')
    ax1.set_ylabel('Temps (secondes)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Graphique du débit
    ax2.plot(user_counts, throughputs, marker='s', linestyle='-', linewidth=2, color='green')
    ax2.set_title('Débit par nombre d\'utilisateurs')
    ax2.set_xlabel('Nombre d\'utilisateurs concurrents')
    ax2.set_ylabel('Requêtes par seconde')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(f"{TEST_CONFIG['output_dir']}/performance_comparison.png")
    
    logger.info(f"Tests de charge terminés. Résumé dans {summary_file}")
    
    # Vérification des métriques de performance
    for result in all_results:
        # S'assurer que le taux de réussite est élevé
        assert result["success_ratio"] > 0.95, f"Taux de réussite trop bas: {result['success_ratio']}"
        
        # Vérifier que les temps de réponse restent dans des limites raisonnables
        # Ceci peut être ajusté en fonction des attentes spécifiques du système
        assert result["statistics"]["p95"] < 10.0, f"Le p95 du temps de réponse est trop élevé: {result['statistics']['p95']}s"


if __name__ == "__main__":
    # Exécution directe (sans pytest)
    asyncio.run(test_rag_performance_scaling()) 