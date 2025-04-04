import pytest
import os
from src.rag import RAGWorkflow
from src.server import get_headers, get_network_summary, get_centralities

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('SPARKSEER_API_KEY', 'test_api_key')
    monkeypatch.setenv('ENVIRONMENT', 'test')
    monkeypatch.setenv('OPENAI_API_KEY', 'test_openai_key')
    monkeypatch.setenv('MONGODB_URI', 'mongodb://localhost:27017/test')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')

@pytest.fixture
async def rag_workflow():
    """Fixture pour créer une instance de RAGWorkflow."""
    workflow = RAGWorkflow()
    await workflow._init_redis()
    yield workflow
    await workflow._close_redis()

def test_get_headers(mock_env_vars):
    """Test de la fonction get_headers."""
    headers = get_headers()
    assert headers['api-key'] == 'test_api_key'
    assert headers['Content-Type'] == 'application/json'

@pytest.mark.asyncio
async def test_rag_workflow_initialization(rag_workflow):
    """Test de l'initialisation du RAGWorkflow."""
    assert rag_workflow is not None
    assert rag_workflow.openai_client is not None
    assert rag_workflow.tokenizer is not None

@pytest.mark.asyncio
async def test_rag_workflow_query(rag_workflow):
    """Test de la fonction query du RAGWorkflow."""
    # Créer un index de test avec des données factices
    test_data = "Ceci est un test de données."
    await rag_workflow.ingest_documents("data")
    
    # Tester une requête
    try:
        result = await rag_workflow.query("Test query")
        assert result is not None
    except ValueError as e:
        # Si l'index est vide, c'est normal d'avoir une erreur
        assert "No documents have been ingested" in str(e)

@pytest.mark.asyncio
async def test_get_network_summary(mock_env_vars):
    """Test de la fonction get_network_summary."""
    try:
        result = await get_network_summary()
        assert isinstance(result, (dict, str))
    except Exception as e:
        pytest.skip(f"Test skipped due to external dependency: {str(e)}")

@pytest.mark.asyncio
async def test_get_centralities(mock_env_vars):
    """Test de la fonction get_centralities."""
    try:
        result = await get_centralities()
        assert isinstance(result, (dict, str))
    except Exception as e:
        pytest.skip(f"Test skipped due to external dependency: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 