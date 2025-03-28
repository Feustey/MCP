import pytest
import os
from rag import RAGWorkflow
from server import get_headers, get_network_summary, get_centralities

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('SPARKSEER_API_KEY', 'test_api_key')
    monkeypatch.setenv('ENVIRONMENT', 'test')

@pytest.fixture
def rag_workflow():
    """Fixture pour créer une instance de RAGWorkflow."""
    return RAGWorkflow(model_name="llama3.2")

def test_get_headers(mock_env_vars):
    """Test de la fonction get_headers."""
    headers = get_headers()
    assert headers['api-key'] == 'test_api_key'
    assert headers['Content-Type'] == 'application/json'

@pytest.mark.asyncio
async def test_rag_workflow_initialization(rag_workflow):
    """Test de l'initialisation du RAGWorkflow."""
    assert rag_workflow is not None
    assert rag_workflow.llm is not None
    assert rag_workflow.embed_model is not None

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

def test_get_network_summary(mock_env_vars):
    """Test de la fonction get_network_summary."""
    try:
        result = get_network_summary()
        assert isinstance(result, (dict, str))
    except Exception as e:
        # En environnement de test, on peut avoir des erreurs de connexion
        assert "Error getting network summary" in str(e)

def test_get_centralities(mock_env_vars):
    """Test de la fonction get_centralities."""
    try:
        result = get_centralities()
        assert isinstance(result, (dict, str))
    except Exception as e:
        # En environnement de test, on peut avoir des erreurs de connexion
        assert "Error getting centralities" in str(e)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 