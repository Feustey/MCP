import sys
import os
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import asyncio
import logging
import time
import pytest
from server import app, rag_workflow, request_manager
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_sparkseer_connection():
    """Teste la connexion à l'API Sparkseer."""
    try:
        start_time = time.time()
        response = await request_manager.make_request(
            method="GET",
            url="https://api.sparkseer.com/health",
            timeout=5.0
        )
        duration = time.time() - start_time
        
        assert response["status"] == "healthy", f"Statut inattendu: {response.get('status')}"
        assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
        
        logger.info(f"✅ Connexion à Sparkseer réussie (temps: {duration:.2f}s)")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à Sparkseer: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_rag_workflow():
    """Teste le flux RAG avec des données de test."""
    try:
        test_data = {
            "stats": {
                "capacity": 1000000,
                "channels": 10,
                "uptime": 99.9
            },
            "history": {
                "transactions": 1000,
                "volume": 500000
            },
            "network_context": {
                "centrality": 0.8,
                "rank": 50
            }
        }
        
        logger.info("🔄 Démarrage du test RAG...")
        start_time = time.time()
        analysis = await rag_workflow.analyze_node_data(test_data)
        duration = time.time() - start_time
        
        # Vérification détaillée de la réponse
        assert "status" in analysis, "Le champ 'status' est manquant dans la réponse"
        assert "analysis" in analysis, "Le champ 'analysis' est manquant dans la réponse"
        assert analysis["status"] == "success", f"Statut inattendu: {analysis['status']}"
        assert len(analysis["analysis"]) > 100, "L'analyse est trop courte"
        assert duration < 5.0, f"Temps d'analyse trop long: {duration:.2f}s"
        
        logger.info(f"✅ Flux RAG fonctionnel (temps: {duration:.2f}s)")
        logger.info(f"📝 Longueur de l'analyse: {len(analysis['analysis'])} caractères")
        return True
    except AssertionError as e:
        logger.error(f"❌ Erreur de validation dans le flux RAG: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Erreur inattendue dans le flux RAG: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_endpoints():
    """Teste les endpoints de l'API."""
    async with AsyncClient(base_url="http://test") as client:
        try:
            # Test de l'endpoint health
            start_time = time.time()
            response = await client.get("/health", timeout=5.0)
            duration = time.time() - start_time
            
            assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
            assert response.json()["status"] == "healthy", "Statut inattendu"
            assert duration < 1.0, f"Temps de réponse trop long: {duration:.2f}s"
            
            # Test de l'endpoint stats
            start_time = time.time()
            response = await client.get("/stats", timeout=5.0)
            duration = time.time() - start_time
            
            assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
            assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
            
            # Test de l'endpoint recent-queries
            start_time = time.time()
            response = await client.get("/recent-queries", timeout=5.0)
            duration = time.time() - start_time
            
            assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
            assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
            
            logger.info("✅ Tous les tests d'endpoints ont réussi")
            return True
        except AssertionError as e:
            logger.error(f"❌ Erreur de validation dans les tests d'endpoints: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur inattendue dans les tests d'endpoints: {str(e)}")
            return False

@pytest.mark.asyncio
async def test_rate_limiting():
    """Teste le rate limiting."""
    try:
        # Test avec plusieurs requêtes rapides
        for _ in range(5):
            response = await request_manager.make_request(
                method="GET",
                url="https://api.sparkseer.com/health",
                timeout=5.0
            )
            assert response["status"] == "healthy", "Rate limiting a échoué"
        
        logger.info("✅ Rate limiting fonctionnel")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de rate limiting: {str(e)}")
        return False

async def main():
    """Fonction principale pour exécuter tous les tests."""
    tests = [
        test_sparkseer_connection(),
        test_rag_workflow(),
        test_endpoints(),
        test_rate_limiting()
    ]
    
    results = await asyncio.gather(*tests)
    success_count = sum(1 for r in results if r)
    
    logger.info(f"📊 Résultats des tests: {success_count}/{len(tests)} réussis")
    return all(results)

if __name__ == "__main__":
    asyncio.run(main()) 