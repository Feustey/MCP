import pytest
import os
from src.rag_config import RAGConfig

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test-api-key')
    monkeypatch.setenv('MONGO_URL', 'mongodb://localhost:27017')

def test_rag_config_defaults(mock_env_vars):
    """Test des valeurs par défaut de RAGConfig."""
    config = RAGConfig()
    
    # Vérification des variables d'environnement injectées
    assert config.openai_api_key == 'test-api-key'
    assert config.mongo_url == 'mongodb://localhost:27017'
    
    # Vérification des valeurs par défaut
    assert config.openai_model == 'gpt-3.5-turbo'
    assert config.redis_url == 'redis://localhost:6379/0'
    assert config.database_name == 'dazlng'
    assert config.chunk_size == 512
    assert config.chunk_overlap == 50
    assert config.max_context_docs == 5

def test_rag_config_override(mock_env_vars):
    """Test de la surcharge des valeurs par défaut."""
    config = RAGConfig(
        openai_model='gpt-4',
        database_name='testdb',
        chunk_size=1024,
        chunk_overlap=100,
        max_context_docs=10
    )
    
    # Vérification des variables d'environnement injectées
    assert config.openai_api_key == 'test-api-key'
    
    # Vérification des valeurs surchargées
    assert config.openai_model == 'gpt-4'
    assert config.database_name == 'testdb'
    assert config.chunk_size == 1024
    assert config.chunk_overlap == 100
    assert config.max_context_docs == 10

def test_rag_config_cache_ttls(mock_env_vars):
    """Test des TTL de cache dans RAGConfig."""
    config = RAGConfig()
    
    assert config.embedding_cache_ttl == 24 * 3600  # 24 heures
    assert config.response_cache_ttl == 3600        # 1 heure
    assert config.context_cache_ttl == 4 * 3600     # 4 heures
    
    # Test avec des valeurs personnalisées
    config = RAGConfig(
        embedding_cache_ttl=12 * 3600,  # 12 heures
        response_cache_ttl=1800,        # 30 minutes
        context_cache_ttl=2 * 3600      # 2 heures
    )
    
    assert config.embedding_cache_ttl == 12 * 3600
    assert config.response_cache_ttl == 1800
    assert config.context_cache_ttl == 2 * 3600 