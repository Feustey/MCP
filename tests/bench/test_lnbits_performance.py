import pytest
import os
import time
import asyncio
import statistics
from typing import Dict, Any, List

# Import le client direct
from src.direct_lnbits import create_invoice, pay_invoice, get_wallet_balance

# Import pour comparer avec le client HTTP externe
import httpx
import json

# Paramètres de benchmark
ITERATIONS = [10, 50]  # Nombre d'itérations
CONCURRENT = [1, 5]    # Niveau de concurrence

# Configuration LNbits externe pour comparaison
EXTERNAL_URL = os.environ.get("LNBITS_EXTERNAL_URL", "http://localhost:5000")
EXTERNAL_INVOICE_KEY = os.environ.get("LNBITS_EXTERNAL_INVOICE_KEY", "")
EXTERNAL_ADMIN_KEY = os.environ.get("LNBITS_EXTERNAL_ADMIN_KEY", "")

# Marque ce test comme un benchmark à exécuter séparément
pytestmark = pytest.mark.benchmark


@pytest.fixture
async def setup_external_client():
    """Configure et retourne un client HTTP pour LNbits externe"""
    headers = {
        "X-Api-Key": EXTERNAL_INVOICE_KEY,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client, headers


@pytest.mark.parametrize("iterations", ITERATIONS)
@pytest.mark.parametrize("concurrency", CONCURRENT)
@pytest.mark.asyncio
async def test_internal_create_invoice(benchmark, iterations, concurrency):
    """Benchmark la création d'invoices avec le client interne"""
    
    # Liste pour stocker les temps de chaque opération
    latencies = []
    
    async def _run_batch():
        batch_latencies = []
        for i in range(iterations // concurrency):
            start = time.time()
            try:
                await create_invoice(amount=1000, memo=f"test-internal-{i}")
                success = True
            except Exception:
                success = False
            
            end = time.time()
            batch_latencies.append((end - start, success))
        
        return batch_latencies
    
    # Exécution des tasks en parallèle
    tasks = [_run_batch() for _ in range(concurrency)]
    results = await asyncio.gather(*tasks)
    
    # Consolidation des résultats
    for batch in results:
        latencies.extend(batch)
    
    # Calcul des métriques
    success_count = sum(1 for lat, success in latencies if success)
    success_rate = success_count / len(latencies) if latencies else 0
    
    # Extrait uniquement les temps des opérations réussies
    success_latencies = [lat for lat, success in latencies if success]
    
    if success_latencies:
        avg_latency = statistics.mean(success_latencies) * 1000  # ms
        p95_latency = sorted(success_latencies)[int(len(success_latencies) * 0.95)] * 1000  # ms
    else:
        avg_latency = 0
        p95_latency = 0
    
    # Attacher les résultats au benchmark
    benchmark.pedantic(
        lambda: None,  # Fonction factice car le benchmark est déjà exécuté manuellement
        iterations=1,  # On a déjà mesuré nous-mêmes
        rounds=1
    )
    
    # Attacher les métriques personnalisées au benchmark
    benchmark.stats.stats.update({
        "iterations": iterations,
        "concurrency": concurrency,
        "success_rate": success_rate * 100,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "throughput": len(success_latencies) / sum(success_latencies) if success_latencies else 0
    })
    
    # Vérifications minimales
    assert success_rate > 0.9, f"Taux de succès trop bas: {success_rate:.2%}"


@pytest.mark.parametrize("iterations", ITERATIONS)
@pytest.mark.parametrize("concurrency", CONCURRENT)
@pytest.mark.asyncio
async def test_external_create_invoice(benchmark, setup_external_client, iterations, concurrency):
    """Benchmark la création d'invoices avec le client externe"""
    
    # Skip si pas de configuration externe
    if not EXTERNAL_INVOICE_KEY or not EXTERNAL_URL:
        pytest.skip("Configuration LNbits externe manquante")
    
    client, headers = await setup_external_client
    
    # Liste pour stocker les temps de chaque opération
    latencies = []
    
    async def _run_batch():
        batch_latencies = []
        for i in range(iterations // concurrency):
            start = time.time()
            try:
                data = {
                    "amount": 1000,
                    "memo": f"test-external-{i}"
                }
                async with client.post(
                    f"{EXTERNAL_URL}/api/v1/payments",
                    headers=headers,
                    json=data
                ) as response:
                    success = response.status_code == 200
            except Exception:
                success = False
            
            end = time.time()
            batch_latencies.append((end - start, success))
        
        return batch_latencies
    
    # Exécution des tasks en parallèle
    tasks = [_run_batch() for _ in range(concurrency)]
    results = await asyncio.gather(*tasks)
    
    # Consolidation des résultats
    for batch in results:
        latencies.extend(batch)
    
    # Calcul des métriques
    success_count = sum(1 for lat, success in latencies if success)
    success_rate = success_count / len(latencies) if latencies else 0
    
    # Extrait uniquement les temps des opérations réussies
    success_latencies = [lat for lat, success in latencies if success]
    
    if success_latencies:
        avg_latency = statistics.mean(success_latencies) * 1000  # ms
        p95_latency = sorted(success_latencies)[int(len(success_latencies) * 0.95)] * 1000  # ms
    else:
        avg_latency = 0
        p95_latency = 0
    
    # Attacher les résultats au benchmark
    benchmark.pedantic(
        lambda: None,
        iterations=1,
        rounds=1
    )
    
    # Attacher les métriques personnalisées au benchmark
    benchmark.stats.stats.update({
        "iterations": iterations,
        "concurrency": concurrency,
        "success_rate": success_rate * 100,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "throughput": len(success_latencies) / sum(success_latencies) if success_latencies else 0
    })
    
    # Vérifications minimales
    assert success_rate > 0.5, f"Taux de succès trop bas: {success_rate:.2%}"


@pytest.mark.asyncio
async def test_crash_recovery():
    """Test de récupération après un crash simulé"""
    # Crée une facture avant le "crash"
    invoices_before = []
    for i in range(5):
        invoice = await create_invoice(amount=1000, memo=f"crash-test-before-{i}")
        invoices_before.append(invoice)
    
    # Simule un crash en fermant et réinitialisant les connexions
    from lnbits_internal.settings_wrapper import init_lnbits_db
    
    # Force une réinitialisation de la BD (simule un redémarrage)
    await asyncio.sleep(1)  # Attente pour s'assurer que les opérations sont terminées
    assert init_lnbits_db(force_init=True), "Échec de la réinitialisation de la BD"
    
    # Vérifie l'intégrité des factures précédentes
    from lnbits_internal.core.crud.payments import get_payment
    
    valid_count = 0
    for invoice in invoices_before:
        payment = await get_payment(invoice.payment_hash)
        if payment:
            valid_count += 1
    
    # Tente de créer de nouvelles factures après le "crash"
    invoices_after = []
    for i in range(3):
        try:
            invoice = await create_invoice(amount=1000, memo=f"crash-test-after-{i}")
            invoices_after.append(invoice)
        except Exception as e:
            print(f"Erreur lors de la création post-crash: {e}")
    
    # Vérifications
    assert valid_count >= len(invoices_before) * 0.8, f"Trop de factures perdues: {valid_count}/{len(invoices_before)}"
    assert len(invoices_after) > 0, "Impossible de créer de nouvelles factures après crash" 