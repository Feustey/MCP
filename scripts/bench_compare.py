#!/usr/bin/env python3
"""
Benchmark comparatif entre LNbits intégré et LNbits externe.
Mesure les performances réelles pour justifier l'intégration.
"""

import os
import sys
import time
import asyncio
import statistics
import psutil
import aiohttp
import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Ajoute le répertoire racine au path pour les imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("benchmark")

# Mode benchmark: "internal" ou "external"
MODES = ["internal", "external", "both"]

class BenchResults:
    """Stockage et analyse des résultats de benchmark"""
    
    def __init__(self, name: str):
        self.name = name
        self.latencies: List[float] = []
        self.start_time: float = 0
        self.end_time: float = 0
        self.start_memory: float = 0
        self.peak_memory: float = 0
        self.end_memory: float = 0
        self.success: int = 0
        self.errors: int = 0
        self.cpu_percent: List[float] = []
        
    def start(self):
        """Démarre le benchmark et capture l'état initial"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
    def log_request(self, latency: float, success: bool):
        """Log une requête individuelle"""
        self.latencies.append(latency)
        if success:
            self.success += 1
        else:
            self.errors += 1
        
        # Capture CPU et mémoire pendant le test
        self.cpu_percent.append(psutil.cpu_percent(interval=None))
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def finish(self):
        """Finalise le benchmark et capture l'état final"""
        self.end_time = time.time()
        self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    def report(self) -> Dict[str, Any]:
        """Génère un rapport de benchmark"""
        total_time = self.end_time - self.start_time
        memory_change = self.end_memory - self.start_memory
        
        if not self.latencies:
            return {
                "name": self.name,
                "error": "No data collected"
            }
            
        return {
            "name": self.name,
            "total_requests": self.success + self.errors,
            "success_rate": self.success / (self.success + self.errors) * 100 if (self.success + self.errors) > 0 else 0,
            "total_time_seconds": total_time,
            "requests_per_second": (self.success + self.errors) / total_time if total_time > 0 else 0,
            "latency": {
                "min_ms": min(self.latencies) * 1000,
                "max_ms": max(self.latencies) * 1000,
                "avg_ms": statistics.mean(self.latencies) * 1000,
                "p50_ms": statistics.median(self.latencies) * 1000,
                "p95_ms": sorted(self.latencies)[int(len(self.latencies) * 0.95)] * 1000 if self.latencies else 0,
                "p99_ms": sorted(self.latencies)[int(len(self.latencies) * 0.99)] * 1000 if len(self.latencies) >= 100 else 0
            },
            "memory": {
                "start_mb": self.start_memory,
                "peak_mb": self.peak_memory,
                "end_mb": self.end_memory,
                "change_mb": memory_change,
                "change_percent": (memory_change / self.start_memory) * 100 if self.start_memory > 0 else 0
            },
            "cpu": {
                "avg_percent": statistics.mean(self.cpu_percent) if self.cpu_percent else 0,
                "max_percent": max(self.cpu_percent) if self.cpu_percent else 0
            },
            "errors": self.errors
        }
    
    def save_report(self, output_dir: str = "benchmark_results"):
        """Sauvegarde le rapport dans un fichier"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{self.name}_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(self.report(), f, indent=2)
        
        logger.info(f"Rapport sauvegardé dans {filename}")


async def bench_internal(concurrency: int, total_requests: int) -> BenchResults:
    """Benchmark LNbits intégré"""
    from src.lnbits_wrapper import LNBitsWrapper
    
    results = BenchResults("lnbits_internal")
    results.start()
    
    # Prépare la division en batches pour le concurrency control
    batch_size = concurrency
    batches = [total_requests // batch_size + (1 if i < total_requests % batch_size else 0) 
               for i in range(batch_size)]
    
    async def process_batch(batch_id: int, count: int):
        for i in range(count):
            request_id = batch_id * (total_requests // batch_size) + i
            start_time = time.time()
            try:
                await LNBitsWrapper.create_invoice(amount=1000, memo=f"internal-bench-{request_id}")
                success = True
            except Exception as e:
                logger.error(f"Erreur interne: {e}")
                success = False
            
            latency = time.time() - start_time
            results.log_request(latency, success)
    
    # Exécute les batches en parallèle
    tasks = [process_batch(i, batches[i]) for i in range(len(batches))]
    await asyncio.gather(*tasks)
    
    results.finish()
    return results


async def bench_external(concurrency: int, total_requests: int, url: str, api_key: str) -> BenchResults:
    """Benchmark LNbits externe via HTTP"""
    results = BenchResults("lnbits_external")
    results.start()
    
    # Client HTTP avec une session partagée
    async with aiohttp.ClientSession() as session:
        # Prépare la division en batches pour le concurrency control
        batch_size = concurrency
        batches = [total_requests // batch_size + (1 if i < total_requests % batch_size else 0) 
                for i in range(batch_size)]
        
        async def process_batch(batch_id: int, count: int):
            for i in range(count):
                request_id = batch_id * (total_requests // batch_size) + i
                
                # Prépare les headers et payload
                headers = {
                    "X-Api-Key": api_key,
                    "Content-Type": "application/json"
                }
                payload = {
                    "amount": 1000,
                    "memo": f"external-bench-{request_id}"
                }
                
                start_time = time.time()
                try:
                    async with session.post(
                        f"{url}/api/v1/payments", 
                        headers=headers, 
                        json=payload,
                        timeout=10
                    ) as response:
                        success = response.status == 200
                        if not success:
                            logger.error(f"Erreur externe: {response.status} - {await response.text()}")
                except Exception as e:
                    logger.error(f"Erreur externe (exception): {e}")
                    success = False
                
                latency = time.time() - start_time
                results.log_request(latency, success)
        
        # Exécute les batches en parallèle
        tasks = [process_batch(i, batches[i]) for i in range(len(batches))]
        await asyncio.gather(*tasks)
    
    results.finish()
    return results


async def run_crash_test(requests_before_crash: int, requests_after_crash: int) -> Dict:
    """Test de crash et recovery"""
    import signal
    from src.lnbits_wrapper import LNBitsWrapper
    import subprocess
    
    logger.info("Démarrage du test de crash et recovery")
    
    # Phase 1: Création d'invoices avant crash
    invoices_before = []
    for i in range(requests_before_crash):
        try:
            invoice = await LNBitsWrapper.create_invoice(amount=1000, memo=f"crash-test-before-{i}")
            invoices_before.append(invoice)
        except Exception as e:
            logger.error(f"Erreur pré-crash: {e}")
    
    logger.info(f"Créé {len(invoices_before)} invoices avant crash")
    
    # Simuler un crash brutal
    pid = os.getpid()
    logger.warning(f"Simulation d'un crash brutal (PID: {pid})")
    
    # Fork et kill le parent (simulation de crash)
    child_pid = os.fork()
    if child_pid == 0:  # Processus enfant
        # Attendre un moment avant de redémarrer pour simuler un redémarrage
        time.sleep(2)
        
        # Phase 2: Récupération et test post-crash
        async def recovery_test():
            # Vérifie l'intégrité des invoices précédentes
            valid_invoices = 0
            for invoice in invoices_before:
                try:
                    # Tente de vérifier si l'invoice existe toujours
                    payment_hash = invoice.get("payment_hash", "")
                    if not payment_hash:
                        continue
                    
                    # Pas d'API directe pour vérifier une invoice par hash dans le wrapper
                    # Utilise un client direct LNBits pour cette vérification
                    from lnbits_internal.core.crud.payments import get_payment
                    payment = await get_payment(payment_hash)
                    
                    if payment:
                        valid_invoices += 1
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification post-crash: {e}")
            
            logger.info(f"Post-crash: {valid_invoices}/{len(invoices_before)} invoices valides")
            
            # Phase 3: Créer de nouvelles invoices pour confirmer que le système fonctionne
            new_invoices = []
            for i in range(requests_after_crash):
                try:
                    invoice = await LNBitsWrapper.create_invoice(amount=1000, memo=f"crash-test-after-{i}")
                    new_invoices.append(invoice)
                except Exception as e:
                    logger.error(f"Erreur post-crash: {e}")
            
            logger.info(f"Créé {len(new_invoices)} nouvelles invoices après crash")
            
            return {
                "invoices_before_crash": len(invoices_before),
                "valid_invoices_after_crash": valid_invoices,
                "new_invoices_created": len(new_invoices),
                "recovery_success_rate": valid_invoices / len(invoices_before) * 100 if invoices_before else 0
            }
        
        result = asyncio.run(recovery_test())
        
        # Sauvegarde du résultat
        os.makedirs("benchmark_results", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"benchmark_results/crash_recovery_{timestamp}.json", "w") as f:
            json.dump(result, f, indent=2)
        
        sys.exit(0)
    else:  # Processus parent
        # Attendre un court moment puis se terminer brutalement
        time.sleep(1)
        os.kill(pid, signal.SIGKILL)


async def main():
    parser = argparse.ArgumentParser(description="Benchmark LNbits (intégré vs externe)")
    parser.add_argument("--mode", choices=MODES, default="both", help="Mode de benchmark")
    parser.add_argument("--concurrency", type=int, default=10, help="Nombre de requêtes concurrentes")
    parser.add_argument("--requests", type=int, default=100, help="Nombre total de requêtes")
    parser.add_argument("--external-url", default="http://localhost:5000", help="URL LNbits externe")
    parser.add_argument("--api-key", help="Clé API pour LNbits externe")
    parser.add_argument("--crash-test", action="store_true", help="Exécuter le test de crash et recovery")
    parser.add_argument("--crash-before", type=int, default=20, help="Requêtes avant crash")
    parser.add_argument("--crash-after", type=int, default=10, help="Requêtes après recovery")
    
    args = parser.parse_args()
    
    if args.crash_test:
        logger.info("Exécution du test de crash et recovery")
        await run_crash_test(args.crash_before, args.crash_after)
        return
    
    # Exécution des benchmarks sélectionnés
    results = []
    
    if args.mode in ["internal", "both"]:
        logger.info(f"Benchmark LNbits intégré: {args.concurrency} concurrency, {args.requests} requêtes")
        results.append(await bench_internal(args.concurrency, args.requests))
    
    if args.mode in ["external", "both"]:
        if not args.api_key:
            logger.error("Clé API requise pour le benchmark externe")
            return
            
        logger.info(f"Benchmark LNbits externe: {args.concurrency} concurrency, {args.requests} requêtes")
        results.append(await bench_external(args.concurrency, args.requests, args.external_url, args.api_key))
    
    # Sauvegarde et affichage des résultats
    for result in results:
        result.save_report()
        
        # Affichage des résultats clés
        report = result.report()
        logger.info(f"=== Résultats pour {report['name']} ===")
        logger.info(f"Throughput: {report['requests_per_second']:.2f} req/sec")
        logger.info(f"Latence moyenne: {report['latency']['avg_ms']:.2f} ms")
        logger.info(f"Latence P95: {report['latency']['p95_ms']:.2f} ms")
        logger.info(f"Mémoire: {report['memory']['start_mb']:.1f} MB → {report['memory']['end_mb']:.1f} MB (+{report['memory']['change_mb']:.1f} MB)")
        logger.info(f"CPU moyen: {report['cpu']['avg_percent']:.1f}%")
        logger.info(f"Taux de succès: {report['success_rate']:.1f}%")
    
    # Comparaison si les deux modes ont été testés
    if args.mode == "both" and len(results) == 2:
        internal = results[0].report()
        external = results[1].report()
        
        logger.info("\n=== Comparaison ===")
        throughput_diff = internal['requests_per_second'] / external['requests_per_second'] if external['requests_per_second'] > 0 else float('inf')
        latency_diff = external['latency']['avg_ms'] / internal['latency']['avg_ms'] if internal['latency']['avg_ms'] > 0 else float('inf')
        
        logger.info(f"Throughput: Interne est {throughput_diff:.2f}x plus rapide")
        logger.info(f"Latence: Interne est {latency_diff:.2f}x plus rapide")
        logger.info(f"Utilisation mémoire: Interne +{internal['memory']['change_mb']:.1f} MB vs Externe +{external['memory']['change_mb']:.1f} MB")


if __name__ == "__main__":
    asyncio.run(main()) 