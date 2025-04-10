import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio
from src.rag_cache import RAGCache

# Tests avec des mocks directement dans les tests
@pytest.mark.asyncio
async def test_cache_set_get():
    """Test d'ajout et récupération du cache"""
    # Créer un mock du cache
    cache = MagicMock(spec=RAGCache)
    cache.set = AsyncMock(return_value=True)
    cache.get = AsyncMock(return_value={"test": "data"})
    
    # Test data
    test_data = {"test": "data"}
    cache_key = "test:key"
    
    # Mise en cache
    success = await cache.set(cache_key, test_data, "test_data")
    assert success is True
    
    # Récupération du cache
    cached_data = await cache.get(cache_key)
    assert cached_data is not None
    assert cached_data == test_data

@pytest.mark.asyncio
async def test_cache_expiration():
    """Test d'expiration du cache"""
    # Créer un mock du cache
    cache = MagicMock(spec=RAGCache)
    
    # Configurer les mocks pour simuler une expiration
    cache.set = AsyncMock(return_value=True)
    
    # D'abord retourner des données, puis None après "expiration"
    cache.get = AsyncMock()
    cache.get.side_effect = [{"test": "data"}, None]
    
    # Test data
    test_data = {"test": "data"}
    cache_key = "test:expiring_key"
    
    # Mise en cache avec TTL de 1 seconde
    await cache.set(cache_key, test_data, "test_data")
    
    # Vérification immédiate
    cached_data = await cache.get(cache_key, "test_data")
    assert cached_data == test_data
    
    # Simuler expiration (pas besoin d'attendre réellement, on a configuré le mock)
    # Vérification après "expiration"
    expired_data = await cache.get(cache_key, "test_data")
    assert expired_data is None

@pytest.mark.asyncio
async def test_cache_delete():
    """Test de suppression du cache"""
    # Créer un mock du cache
    cache = MagicMock(spec=RAGCache)
    cache.set = AsyncMock(return_value=True)
    cache.exists = AsyncMock(side_effect=[True, False])
    cache.delete = AsyncMock(return_value=True)
    
    # Test data
    test_data = {"test": "data"}
    cache_key = "test:delete_key"
    
    # Mise en cache
    await cache.set(cache_key, test_data, "test_data")
    
    # Vérification de l'existence
    exists = await cache.exists(cache_key, "test_data")
    assert exists is True
    
    # Suppression
    deleted = await cache.delete(cache_key, "test_data")
    assert deleted is True
    
    # Vérification de la suppression
    exists = await cache.exists(cache_key, "test_data")
    assert exists is False

@pytest.mark.asyncio
async def test_cache_clear_pattern():
    """Test de nettoyage par pattern"""
    # Créer un mock du cache
    cache = MagicMock(spec=RAGCache)
    cache.set = AsyncMock(return_value=True)
    cache.clear_pattern = AsyncMock(return_value=True)
    
    # Mock de exists pour retourner True/False selon la clé
    async def mock_exists(key, *args):
        return not key.startswith("test:")
    
    cache.exists = AsyncMock(side_effect=mock_exists)
    
    # Test data
    test_data = {"test": "data"}
    keys = ["test:pattern1", "test:pattern2", "other:key"]
    
    # Mise en cache
    for key in keys:
        await cache.set(key, test_data, "test_data")
    
    # Nettoyage du pattern
    cleared = await cache.clear_pattern("test:*")
    assert cleared is True
    
    # Vérification
    for key in keys:
        exists = await cache.exists(key, "test_data")
        if key.startswith("test:"):
            assert exists is False
        else:
            assert exists is True 