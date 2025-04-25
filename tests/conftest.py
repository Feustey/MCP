"""
Tests pour l'application MCP.
"""
import pytest
import os
from dotenv import load_dotenv
import asyncio
from typing import Generator, AsyncGenerator, Any
from src.rag import RAGWorkflow
from src.mongo_operations import MongoOperations
from src.redis_operations import RedisOperations
import shutil
from datetime import datetime, timedelta
from auth.security import SecurityManager
from src.rag_workflow import RAGWorkflow
from src.rag_cache import RAGCache
from unittest.mock import AsyncMock, Mock, MagicMock, patch

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
    
    # Configuration des marqueurs personnalisés
    config.addinivalue_line("markers", "integration: tests d'intégration avec des services externes")
    config.addinivalue_line("markers", "performance: tests de performance sous charge")
    config.addinivalue_line("markers", "slow: tests qui prennent plus de temps à s'exécuter")
    config.addinivalue_line("markers", "security: tests de sécurité")

@pytest.fixture(autouse=True)
def setup_test_env():
    """Configuration automatique de l'environnement de test"""
    # Sauvegarde des variables d'environnement originales
    original_env = dict(os.environ)
    
    # Configuration de l'environnement de test
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['MONGODB_URI'] = 'mongodb+srv://feustey:VwSrcnNI8i5m2sim@dazlng.ug0aiaw.mongodb.net/?retryWrites=true&w=majority&appName=DazLng'
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['SPARKSEER_API_KEY'] = 'test_api_key'
    os.environ['OPENAI_API_KEY'] = 'test_openai_key'
    os.environ['AMBOSS_API_KEY'] = 'test_amboss_key'
    os.environ['JWT_SECRET'] = 'test_secret_key'
    
    yield
    
    # Restauration des variables d'environnement originales
    os.environ.clear()
    os.environ.update(original_env)

# Utiliser pytest-asyncio pour gérer les loops asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Crée une nouvelle boucle d'événements pour chaque session de test"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Créer un répertoire temporaire pour les données de test."""
    return tmp_path_factory.mktemp("test_data")

@pytest.fixture
async def redis_ops():
    """Fixture pour les opérations Redis"""
    redis_ops = RedisOperations(os.getenv('REDIS_URL'))
    await redis_ops._init_redis()
    try:
        yield redis_ops
    finally:
        await redis_ops._close_redis()

@pytest.fixture
async def mongo_ops():
    """Fixture pour les opérations MongoDB"""
    ops = MongoOperations()
    await ops.connect()
    # Nettoyage des collections avant les tests
    await ops.db.documents.delete_many({})
    await ops.db.query_history.delete_many({})
    await ops.db.system_stats.delete_many({})
    yield ops
    await ops.close()

@pytest.fixture
async def rag_workflow():
    """Fixture pour le workflow RAG"""
    workflow = RAGWorkflow()
    await workflow.initialize()
    yield workflow
    await workflow.close()

@pytest.fixture
async def cache_manager():
    """Fixture pour le gestionnaire de cache"""
    cache = RAGCache()
    await cache.initialize()
    yield cache
    await cache.close()

@pytest.fixture
def mock_client():
    """Mock pour les clients HTTP"""
    with patch('httpx.AsyncClient') as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        mock.return_value.__aenter__.return_value = client_instance
        yield mock

@pytest.fixture
def test_env():
    """Configure l'environnement de test."""
    # Sauvegarder les variables d'environnement
    old_env = {}
    for key in ["JWT_SECRET_KEY", "JWT_ALGORITHM"]:
        if key in os.environ:
            old_env[key] = os.environ[key]
    
    # Définir les variables d'environnement pour les tests
    os.environ["JWT_SECRET_KEY"] = "test_secret_key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    
    yield
    
    # Restaurer les variables d'environnement
    for key, value in old_env.items():
        os.environ[key] = value
    for key in ["JWT_SECRET_KEY", "JWT_ALGORITHM"]:
        if key not in old_env and key in os.environ:
            del os.environ[key]

@pytest.fixture
def test_keys_dir():
    """Crée un répertoire temporaire pour les clés de test."""
    test_dir = "test_keys"
    os.makedirs(test_dir, exist_ok=True)
    yield test_dir
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

@pytest.fixture
def security_manager(test_env, test_keys_dir):
    """Crée un SecurityManager pour les tests."""
    manager = SecurityManager()
    manager.keys_dir = test_keys_dir
    return manager 

# Standardisation des mocks
@pytest.fixture
def standard_mocks():
    """Fournit un ensemble standardisé de mocks pour les tests.
    
    Returns:
        dict: Dictionnaire contenant les mocks standard
    """
    mocks = {}
    
    # Mock pour OpenAI
    mocks["openai"] = MagicMock()
    mocks["openai"].embeddings.create = AsyncMock(return_value=MagicMock(
        data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
    ))
    mocks["openai"].chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(
            message=MagicMock(content="Réponse de test")
        )]
    ))
    
    # Mock pour Redis
    mocks["redis"] = AsyncMock()
    mocks["redis"].get = AsyncMock(return_value=None)
    mocks["redis"].set = AsyncMock(return_value=True)
    mocks["redis"].exists = AsyncMock(return_value=0)
    mocks["redis"].delete = AsyncMock(return_value=1)
    
    # Mock pour MongoDB
    mocks["mongodb"] = MagicMock()
    mocks["mongodb"].find_one.return_value = {"_id": "test_id", "content": "Test document"}
    mocks["mongodb"].insert_one.return_value = MagicMock(inserted_id="new_id")
    mocks["mongodb"].find.return_value = MagicMock(
        to_list=AsyncMock(return_value=[{"_id": "test_id", "content": "Test document"}])
    )
    
    # Mock pour HTTP
    mocks["http"] = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={})
    mocks["http"].get = AsyncMock(return_value=response)
    mocks["http"].post = AsyncMock(return_value=response)
    
    return mocks

@pytest.fixture(scope="session")
def performance_config():
    """Configuration pour les tests de performance."""
    return {
        "concurrent_users": [1, 5, 10, 20],
        "requests_per_user": 10,
        "request_delay": 0.1,
        "output_dir": "tests/load_tests/results"
    } 