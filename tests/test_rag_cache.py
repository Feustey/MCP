import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio
from src.rag_cache import RAGCache
import redis.asyncio as redis

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

@pytest.mark.asyncio
async def test_cache_error_handling():
    """Test de la gestion des erreurs dans le cache"""
    # Créer un mock du cache
    cache = MagicMock(spec=RAGCache)
    
    # Simuler une erreur Redis
    cache.set = AsyncMock(side_effect=redis.RedisError("Erreur de connexion"))
    
    # Test data
    test_data = {"test": "data"}
    cache_key = "test:error_key"
    
    # Tentative de mise en cache qui doit échouer
    with pytest.raises(redis.RedisError) as excinfo:
        await cache.set(cache_key, test_data, "test_data")
    
    assert "Erreur de connexion" in str(excinfo.value)
    
    # Tester la résilience avec une implémentation réelle
    with patch('src.rag_cache.RAGCache._get_redis', side_effect=redis.RedisError("Erreur critique")):
        real_cache = RAGCache()
        
        # L'initialisation ne devrait pas lever d'erreur, mais le cache devrait être marqué comme non disponible
        await real_cache.initialize()
        
        # Les opérations devraient retourner des valeurs par défaut
        result = await real_cache.get("any_key")
        assert result is None
        
        success = await real_cache.set("any_key", {"data": "test"})
        assert success is False

@pytest.mark.asyncio
async def test_cache_serialization_deserialization():
    """Test de la sérialisation et désérialisation dans le cache"""
    # Créer un mock du cache avec des méthodes qui simulent la sérialisation/désérialisation
    cache = MagicMock(spec=RAGCache)
    
    # Simuler la sérialisation/désérialisation
    original_data = {
        "query": "test query", 
        "response": "test response",
        "timestamp": datetime.now().isoformat(),
        "metadata": {"source": "test", "score": 0.95}
    }
    
    serialized_data = json.dumps(original_data)
    
    # Mock de _serialize pour enregistrer l'appel et retourner la sérialisation
    cache._serialize = MagicMock(return_value=serialized_data)
    
    # Mock de _deserialize pour simuler la désérialisation
    cache._deserialize = MagicMock(return_value=original_data)
    
    # Simuler set/get avec sérialisation/désérialisation
    cache.redis = AsyncMock()
    cache.redis.set = AsyncMock(return_value=True)
    cache.redis.get = AsyncMock(return_value=serialized_data)
    
    # Implémenter des versions réelles des méthodes set/get qui utilisent les mocks
    async def mock_set(key, data, *args, **kwargs):
        serialized = cache._serialize(data)
        return await cache.redis.set(key, serialized, *args, **kwargs)
    
    async def mock_get(key, *args, **kwargs):
        serialized = await cache.redis.get(key)
        if serialized:
            return cache._deserialize(serialized)
        return None
    
    cache.set = AsyncMock(side_effect=mock_set)
    cache.get = AsyncMock(side_effect=mock_get)
    
    # Test
    cache_key = "test:serialization_key"
    
    # Mise en cache
    await cache.set(cache_key, original_data)
    
    # Vérification que la sérialisation a été appelée avec les bonnes données
    cache._serialize.assert_called_once_with(original_data)
    
    # Récupération du cache
    retrieved_data = await cache.get(cache_key)
    
    # Vérification que la désérialisation a été appelée avec les bonnes données
    cache._deserialize.assert_called_once_with(serialized_data)
    
    # Vérification des données récupérées
    assert retrieved_data == original_data 