import pytest
from fastapi.testclient import TestClient
from server import app
import jwt
import os
from unittest.mock import patch, MagicMock

client = TestClient(app)

def get_test_token():
    """Génère un token JWT de test."""
    secret = os.getenv("JWT_SECRET", "your-secret-key")
    payload = {"sub": "test-user", "role": "user"}
    return jwt.encode(payload, secret, algorithm="HS256")

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the RAG API"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_query_without_auth():
    """Test que l'endpoint /query requiert une authentification."""
    response = client.post("/query", params={"query_text": "test query"})
    assert response.status_code == 403
    
@patch('rag.RAGWorkflow.query')
def test_query_with_auth(mock_query):
    """Test que l'endpoint /query fonctionne avec une authentification valide."""
    # Configuration du mock
    mock_query.return_value = "Réponse de test"
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/query", params={"query_text": "test query"}, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"response": "Réponse de test"}
    mock_query.assert_called_once_with("test query")
    
def test_ingest_without_auth():
    """Test que l'endpoint /ingest requiert une authentification."""
    response = client.post("/ingest", params={"directory": "test_docs"})
    assert response.status_code == 403
    
@patch('rag.RAGWorkflow.ingest_documents')
def test_ingest_with_auth(mock_ingest):
    """Test que l'endpoint /ingest fonctionne avec une authentification valide."""
    # Configuration du mock
    mock_ingest.return_value = True
    
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/ingest", params={"directory": "test_docs"}, headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_ingest.assert_called_once_with("test_docs") 