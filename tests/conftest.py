import pytest
import os
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Créer une instance de l'event loop pour les tests asynchrones."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Créer un répertoire temporaire pour les données de test."""
    return tmp_path_factory.mktemp("test_data") 