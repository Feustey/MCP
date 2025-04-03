import asyncio
import logging
import time
from server import app, router, rag_workflow, request_manager
from fastapi.testclient import TestClient

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sparkseer_connection():
    """Teste la connexion à l'API Sparkseer."""
    try:
        start_time = time.time()
        response = await request_manager.make_request(
            method="GET",
            url="https://api.sparkseer.com/health"
        )
        duration = time.time() - start_time
        
        assert response["status"] == "healthy", f"Statut inattendu: {response.get('status')}"
        assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
        
        logger.info(f"✅ Connexion à Sparkseer réussie (temps: {duration:.2f}s)")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à Sparkseer: {str(e)}")
        return False

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

async def test_endpoints():
    """Teste les endpoints de l'API."""
    client = TestClient(app=app)
    
    try:
        # Test de l'endpoint health
        start_time = time.time()
        response = client.get("/health")
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
        assert response.json()["status"] == "healthy", "Statut inattendu"
        assert duration < 1.0, f"Temps de réponse trop long: {duration:.2f}s"
        
        # Test de l'endpoint network-summary
        start_time = time.time()
        response = client.get("/network-summary")
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
        assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
        
        # Test de l'endpoint centralities
        start_time = time.time()
        response = client.get("/centralities")
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}"
        assert duration < 2.0, f"Temps de réponse trop long: {duration:.2f}s"
        
        logger.info("✅ Endpoints API fonctionnels")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur dans les endpoints: {str(e)}")
        return False

async def test_rate_limiting():
    """Teste la gestion du rate limiting."""
    try:
        # Simuler plusieurs requêtes rapides
        tasks = []
        for _ in range(5):
            tasks.append(request_manager.make_request(
                method="GET",
                url="https://api.sparkseer.com/health"
            ))
        
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r is not None)
        
        assert success_count > 0, "Aucune requête n'a réussi"
        logger.info(f"✅ Test de rate limiting réussi ({success_count}/5 requêtes)")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de rate limiting: {str(e)}")
        return False

async def main():
    """Exécute tous les tests."""
    logger.info("🚀 Démarrage des tests...")
    
    # Test de la connexion Sparkseer
    sparkseer_ok = await test_sparkseer_connection()
    
    # Test du flux RAG
    rag_ok = await test_rag_workflow()
    
    # Test des endpoints
    endpoints_ok = await test_endpoints()
    
    # Test du rate limiting
    rate_limit_ok = await test_rate_limiting()
    
    # Nettoyage du cache
    await rag_workflow.cleanup_cache()
    
    # Résumé des tests
    logger.info("\n📊 Résumé des tests:")
    logger.info(f"Sparkseer: {'✅' if sparkseer_ok else '❌'}")
    logger.info(f"RAG: {'✅' if rag_ok else '❌'}")
    logger.info(f"Endpoints: {'✅' if endpoints_ok else '❌'}")
    logger.info(f"Rate Limiting: {'✅' if rate_limit_ok else '❌'}")

if __name__ == "__main__":
    asyncio.run(main()) 