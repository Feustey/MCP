import asyncio
import time
from datetime import datetime
import logging
from typing import List, Dict, Any
from src.rag_data_provider import RAGDataProvider
from rag import RAGWorkflow
import json
import statistics

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGBenchmark:
    def __init__(self):
        self.data_provider = RAGDataProvider()
        self.rag = RAGWorkflow()
        self.results: List[Dict[str, Any]] = []
        
    async def run_benchmark(self, queries: List[str], iterations: int = 5):
        """Exécute le benchmark sur un ensemble de requêtes"""
        logger.info(f"Démarrage du benchmark avec {len(queries)} requêtes, {iterations} itérations")
        
        for query in queries:
            query_results = []
            
            for i in range(iterations):
                logger.info(f"Test de la requête '{query}' (itération {i+1}/{iterations})")
                
                start_time = time.time()
                try:
                    # Récupération du contexte
                    context = await self.data_provider.get_context_data(query)
                    context_time = time.time() - start_time
                    
                    # Génération de la réponse
                    response_start = time.time()
                    response = await self.rag.query(query, context=context)
                    response_time = time.time() - response_start
                    
                    # Calcul des métriques
                    total_time = time.time() - start_time
                    
                    result = {
                        "query": query,
                        "iteration": i + 1,
                        "context_time": context_time,
                        "response_time": response_time,
                        "total_time": total_time,
                        "success": True,
                        "error": None
                    }
                    
                except Exception as e:
                    result = {
                        "query": query,
                        "iteration": i + 1,
                        "context_time": None,
                        "response_time": None,
                        "total_time": None,
                        "success": False,
                        "error": str(e)
                    }
                
                query_results.append(result)
                
            # Analyse des résultats pour cette requête
            self._analyze_query_results(query, query_results)
            
        # Sauvegarde des résultats
        self._save_results()
        
    def _analyze_query_results(self, query: str, results: List[Dict[str, Any]]):
        """Analyse les résultats pour une requête"""
        successful_results = [r for r in results if r["success"]]
        
        if successful_results:
            analysis = {
                "query": query,
                "total_iterations": len(results),
                "successful_iterations": len(successful_results),
                "success_rate": len(successful_results) / len(results),
                "avg_context_time": statistics.mean(r["context_time"] for r in successful_results),
                "avg_response_time": statistics.mean(r["response_time"] for r in successful_results),
                "avg_total_time": statistics.mean(r["total_time"] for r in successful_results),
                "min_total_time": min(r["total_time"] for r in successful_results),
                "max_total_time": max(r["total_time"] for r in successful_results),
                "std_dev_total_time": statistics.stdev(r["total_time"] for r in successful_results) if len(successful_results) > 1 else 0
            }
            
            self.results.append(analysis)
            
            # Log des résultats
            logger.info(f"\nRésultats pour la requête '{query}':")
            logger.info(f"Taux de succès: {analysis['success_rate']*100:.2f}%")
            logger.info(f"Temps moyen total: {analysis['avg_total_time']:.2f}s")
            logger.info(f"Écart-type: {analysis['std_dev_total_time']:.2f}s")
            
    def _save_results(self):
        """Sauvegarde les résultats du benchmark"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.results
            }, f, indent=2)
            
        logger.info(f"Résultats sauvegardés dans {filename}")

async def main():
    # Requêtes de test
    test_queries = [
        "Quelle est la capacité totale du réseau Lightning?",
        "Quels sont les nœuds les plus performants?",
        "Comment optimiser les frais de transaction?",
        "Quelles sont les meilleures pratiques de sécurité?",
        "Comment gérer la liquidité des canaux?"
    ]
    
    # Exécution du benchmark
    benchmark = RAGBenchmark()
    await benchmark.run_benchmark(test_queries, iterations=3)

if __name__ == "__main__":
    asyncio.run(main()) 