import pytest
import asyncio
import logging
from fastapi.testclient import TestClient
from httpx import AsyncClient
from server import app
import jwt
import os
from unittest.mock import patch, MagicMock

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_test_token():
    """Génère un token JWT de test."""
    secret = os.getenv("JWT_SECRET", "your-secret-key")
    payload = {"sub": "test-user", "role": "user"}
    return jwt.encode(payload, secret, algorithm="HS256")

@pytest.mark.asyncio
async def test_read_root():
    """Test de l'endpoint racine."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"message": "Welcome to the RAG API"}
            logger.info("✅ Test de l'endpoint racine réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint racine: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_health():
    """Test de l'endpoint health."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health", timeout=5.0)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
            logger.info("✅ Test de l'endpoint health réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint health: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_query_without_auth():
    """Test que l'endpoint /query requiert une authentification."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/query", params={"query_text": "test query"}, timeout=5.0)
            assert response.status_code == 403
            logger.info("✅ Test d'authentification manquante réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test d'authentification manquante: {str(e)}")
        return False

@pytest.mark.asyncio
@patch('rag.RAGWorkflow.query')
async def test_query_with_auth(mock_query):
    """Test que l'endpoint /query fonctionne avec une authentification valide."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Configuration du mock
            mock_query.return_value = "Réponse de test"
            
            token = get_test_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(
                "/query",
                params={"query_text": "test query"},
                headers=headers,
                timeout=5.0
            )
            
            assert response.status_code == 200
            assert response.json() == {"response": "Réponse de test"}
            mock_query.assert_called_once_with("test query")
            logger.info("✅ Test de l'endpoint query avec auth réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint query avec auth: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_ingest_without_auth():
    """Test que l'endpoint /ingest requiert une authentification."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/ingest", params={"directory": "test_docs"}, timeout=5.0)
            assert response.status_code == 403
            logger.info("✅ Test d'authentification manquante pour ingest réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test d'authentification manquante pour ingest: {str(e)}")
        return False

@pytest.mark.asyncio
@patch('rag.RAGWorkflow.ingest_documents')
async def test_ingest_with_auth(mock_ingest):
    """Test que l'endpoint /ingest fonctionne avec une authentification valide."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Configuration du mock
            mock_ingest.return_value = True
            
            token = get_test_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.post(
                "/ingest",
                params={"directory": "test_docs"},
                headers=headers,
                timeout=5.0
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            mock_ingest.assert_called_once_with("test_docs")
            logger.info("✅ Test de l'endpoint ingest avec auth réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint ingest avec auth: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_stats_without_auth():
    """Test que l'endpoint /stats requiert une authentification."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/stats", timeout=5.0)
            assert response.status_code == 403
            logger.info("✅ Test d'authentification manquante pour stats réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test d'authentification manquante pour stats: {str(e)}")
        return False

@pytest.mark.asyncio
@patch('mongo_operations.MongoOperations.get_system_stats')
async def test_stats_with_auth(mock_stats):
    """Test que l'endpoint /stats fonctionne avec une authentification valide."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Configuration du mock
            mock_stats.return_value = MagicMock(
                model_dump=lambda: {
                    "total_queries": 100,
                    "success_rate": 0.95,
                    "average_response_time": 0.5
                }
            )
            
            token = get_test_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/stats", headers=headers, timeout=5.0)
            
            assert response.status_code == 200
            assert "total_queries" in response.json()
            assert "success_rate" in response.json()
            assert "average_response_time" in response.json()
            logger.info("✅ Test de l'endpoint stats avec auth réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint stats avec auth: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_recent_queries_without_auth():
    """Test que l'endpoint /recent-queries requiert une authentification."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/recent-queries", timeout=5.0)
            assert response.status_code == 403
            logger.info("✅ Test d'authentification manquante pour recent-queries réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test d'authentification manquante pour recent-queries: {str(e)}")
        return False

@pytest.mark.asyncio
@patch('mongo_operations.MongoOperations.get_recent_queries')
async def test_recent_queries_with_auth(mock_queries):
    """Test que l'endpoint /recent-queries fonctionne avec une authentification valide."""
    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Configuration du mock
            mock_queries.return_value = [
                {"query": "test1", "timestamp": "2024-02-20T10:00:00"},
                {"query": "test2", "timestamp": "2024-02-20T09:00:00"}
            ]
            
            token = get_test_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get("/recent-queries", headers=headers, timeout=5.0)
            
            assert response.status_code == 200
            assert len(response.json()) == 2
            assert "query" in response.json()[0]
            assert "timestamp" in response.json()[0]
            logger.info("✅ Test de l'endpoint recent-queries avec auth réussi")
            return True
    except Exception as e:
        logger.error(f"❌ Erreur dans le test de l'endpoint recent-queries avec auth: {str(e)}")
        return False 