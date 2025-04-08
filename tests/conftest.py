import pytest
import os
from dotenv import load_dotenv
import asyncio
from typing import Generator

# Chargement des variables d'environnement
load_dotenv()

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
    
    yield
    
    # Restauration des variables d'environnement originales
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Créer une instance de l'event loop pour les tests asynchrones."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Créer un répertoire temporaire pour les données de test."""
    return tmp_path_factory.mktemp("test_data") 