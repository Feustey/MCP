import pytest
import time
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.cache_manager import CacheManager

@pytest.fixture
def cache_manager():
    """Fixture pour créer un CacheManager."""
    cm = CacheManager()
    return cm

@pytest.mark.asyncio
async def test_cache_manager_init():
    """Test de l'initialisation du CacheManager."""
    cm = CacheManager()
    assert cm.cache == {}
    assert cm.timestamps == {}
    assert cm.cache_ttls["embedding"] == 24 * 3600
    assert cm.cache_ttls["response"] == 3600
    assert cm.cache_ttls["context"] == 4 * 3600

@pytest.mark.asyncio
async def test_initialize():
    """Test de la méthode initialize avec un client Redis."""
    mock_redis = AsyncMock()
    cm = CacheManager()
    result = await cm.initialize(redis_client=mock_redis)
    
    assert cm.redis_client == mock_redis
    assert result == cm

@pytest.mark.asyncio
async def test_get_not_expired(cache_manager):
    """Test de la méthode get avec une clé non expirée."""
    # Setup: Ajouter une entrée dans le cache
    cache_manager.cache["test_key"] = "test_value"
    cache_manager.timestamps["test_key"] = time.time()  # timestamp actuel
    
    # Action & Assert
    value = await cache_manager.get("test_key")
    assert value == "test_value"

@pytest.mark.asyncio
async def test_get_expired(cache_manager):
    """Test de la méthode get avec une clé expirée."""
    # Setup: Ajouter une entrée expirée dans le cache
    cache_manager.cache["test_key"] = "test_value"
    cache_manager.timestamps["test_key"] = time.time() - 7200  # 2 heures dans le passé
    cache_manager.cache_ttls["default"] = 3600  # 1 heure TTL
    
    # Patch de la méthode _is_expired pour simuler l'expiration
    with patch.object(cache_manager, '_is_expired', return_value=True):
        # Action & Assert
        value = await cache_manager.get("test_key")
        assert value is None

@pytest.mark.asyncio
async def test_get_missing(cache_manager):
    """Test de la méthode get avec une clé manquante."""
    # Action & Assert
    value = await cache_manager.get("nonexistent_key")
    assert value is None

@pytest.mark.asyncio
async def test_set(cache_manager):
    """Test de la méthode set."""
    # Setup
    current_time = time.time()
    with patch('time.time', return_value=current_time):
        # Action
        await cache_manager.set("test_key", "test_value")
        
        # Assert
        assert cache_manager.cache["test_key"] == "test_value"
        assert cache_manager.timestamps["test_key"] == current_time

@pytest.mark.asyncio
async def test_set_with_custom_ttl(cache_manager):
    """Test de la méthode set avec TTL personnalisé."""
    # Action
    await cache_manager.set("test_key", "test_value", ttl=7200)
    
    # Assert
    assert cache_manager.cache["test_key"] == "test_value"
    assert "test_key" in cache_manager.timestamps

@pytest.mark.asyncio
async def test_set_with_prefix(cache_manager):
    """Test de la méthode set avec préfixe de clé."""
    # Action
    await cache_manager.set("embedding:test", "test_embedding")
    
    # Assert
    assert cache_manager.cache["embedding:test"] == "test_embedding"
    assert "embedding:test" in cache_manager.timestamps

@pytest.mark.asyncio
async def test_delete_existing(cache_manager):
    """Test de la méthode delete avec une clé existante."""
    # Setup
    cache_manager.cache["test_key"] = "test_value"
    cache_manager.timestamps["test_key"] = time.time()
    
    # Action
    result = await cache_manager.delete("test_key")
    
    # Assert
    assert result is True
    assert "test_key" not in cache_manager.cache
    assert "test_key" not in cache_manager.timestamps

@pytest.mark.asyncio
async def test_delete_nonexistent(cache_manager):
    """Test de la méthode delete avec une clé inexistante."""
    # Action
    result = await cache_manager.delete("nonexistent_key")
    
    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_is_expired(cache_manager):
    """Test de la méthode _is_expired."""
    # Setup
    current_time = time.time()
    
    # Cas 1: Clé non expirée
    cache_manager.timestamps["recent_key"] = current_time
    # Cas 2: Clé expirée
    cache_manager.timestamps["old_key"] = current_time - 7200  # 2 heures dans le passé
    cache_manager.cache_ttls["default"] = 3600  # 1 heure TTL
    
    # Action & Assert
    assert cache_manager._is_expired("nonexistent_key") is True  # Clé manquante
    assert cache_manager._is_expired("old_key") is True  # Clé expirée
    assert cache_manager._is_expired("recent_key") is False  # Clé non expirée

@pytest.mark.asyncio
async def test_clear_expired_cache(cache_manager):
    """Test de la méthode clear_expired_cache."""
    # Setup
    current_time = time.time()
    
    # Ajouter des entrées au cache
    cache_manager.cache["fresh_key"] = "fresh_value"
    cache_manager.timestamps["fresh_key"] = current_time
    
    cache_manager.cache["expired_key"] = "expired_value"
    cache_manager.timestamps["expired_key"] = current_time - 7200  # 2 heures dans le passé
    cache_manager.cache_ttls["default"] = 3600  # 1 heure TTL
    
    # Mock la méthode _is_expired pour simuler l'expiration
    with patch.object(cache_manager, '_is_expired', side_effect=lambda key: key == "expired_key"):
        # Action
        result = await cache_manager.clear_expired_cache()
        
        # Assert
        assert result is True
        assert "fresh_key" in cache_manager.cache
        assert "expired_key" not in cache_manager.cache

@pytest.mark.asyncio
async def test_clear_expired_cache_with_redis(cache_manager):
    """Test de la méthode clear_expired_cache avec Redis."""
    # Setup
    mock_redis = AsyncMock()
    mock_redis.keys = AsyncMock(return_value=["embedding:test1", "embedding:test2"])
    mock_pipeline = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
    
    cache_manager.redis_client = mock_redis
    
    # Action
    result = await cache_manager.clear_expired_cache()
    
    # Assert
    assert result is True
    mock_redis.keys.assert_called()
    mock_pipeline.delete.assert_called()
    mock_pipeline.execute.assert_called_once() 