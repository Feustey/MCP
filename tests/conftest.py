"""
Tests pour l'application MCP.
"""
import pytest
import os
from dotenv import load_dotenv
import asyncio
from typing import Generator, AsyncGenerator
from rag import RAGWorkflow
from rag.mongo_operations import MongoOperations
from rag.redis_operations import RedisOperations
from src.llm_selector import OllamaLLM

# Chargement des variables d'environnement de test
load_dotenv('.env.test')

def pytest_configure(config):
    """Configuration de pytest"""
    # Vérification des variables d'environnement requises
    required_env_vars = [
        'MONGODB_URI',
        'OPENAI_API_KEY',
        'REDIS_URL'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        pytest.exit(f"Variables d'environnement manquantes: {', '.join(missing_vars)}")

@pytest.fixture(autouse=True)
def setup_test_env():
    """Configuration automatique de l'environnement de test"""
    # Sauvegarde des variables d'environnement originales
    original_env = dict(os.environ)
    
    # Configuration de l'environnement de test
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/test'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['SPARKSEER_API_KEY'] = 'test_api_key'
    os.environ['OPENAI_API_KEY'] = 'test_openai_key'
    os.environ['AMBOSS_API_KEY'] = 'test_amboss_key'
    os.environ['JWT_SECRET'] = 'test_secret_key'
    
    yield
    
    # Restauration des variables d'environnement originales
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture(scope="session")
def event_loop():
    """Créer une instance de l'event loop pour les tests asynchrones."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Créer un répertoire temporaire pour les données de test."""
    return tmp_path_factory.mktemp("test_data")

@pytest.fixture
async def redis_ops() -> AsyncGenerator[RedisOperations, None]:
    """Fixture pour les opérations Redis"""
    redis_ops = RedisOperations(os.getenv('REDIS_URL'))
    await redis_ops._init_redis()
    try:
        yield redis_ops
    finally:
        await redis_ops._close_redis()

@pytest.fixture
async def mongo_ops() -> AsyncGenerator[MongoOperations, None]:
    """Fixture pour les opérations MongoDB"""
    mongo_ops = MongoOperations()
    await mongo_ops.connect()
    await mongo_ops.db.documents.delete_many({})
    await mongo_ops.db.query_history.delete_many({})
    await mongo_ops.db.system_stats.delete_many({})
    try:
        yield mongo_ops
    finally:
        await mongo_ops.close()

@pytest.fixture
async def test_llm():
    """Fixture pour un LLM de test."""
    return OllamaLLM(model="llama3")

@pytest.fixture
async def rag_workflow(redis_ops: RedisOperations, test_llm) -> AsyncGenerator[RAGWorkflow, None]:
    """Fixture pour le workflow RAG"""
    workflow = RAGWorkflow(llm=test_llm, redis_ops=redis_ops)
    await workflow.ensure_connected()
    try:
        yield workflow
    finally:
        await workflow.close_connections() 