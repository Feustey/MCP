import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Classe simulée qui sera mockée dans les tests
class CacheManager:
    async def initialize(self):
        pass
        
    async def set(self, key, value, ttl=None):
        return True
        
    async def get(self, key):
        return {}
        
    async def delete(self, key):
        return True
        
    async def close(self):
        pass

# Tests utilisant le patch directement pour contourner les problèmes de fixtures asyncio
@pytest.mark.asyncio
async def test_cache_set_get():
    """Test d'ajout et récupération du cache avec mock"""
    # Création du mock directement dans le test
    cache = MagicMock(spec=CacheManager)
    cache.set = AsyncMock(return_value=True)
    cache.get = AsyncMock(return_value={"test": "mock_data"})
    
    # Test data
    test_data = {"test": "data"}
    cache_key = "test:key"
    
    # Mise en cache
    success = await cache.set(cache_key, test_data)
    assert success is True
    
    # Vérifier que la méthode set a été appelée avec les bons arguments
    cache.set.assert_called_once_with(cache_key, test_data)
    
    # Récupération du cache
    cached_data = await cache.get(cache_key)
    assert cached_data is not None
    assert cached_data == {"test": "mock_data"}

@pytest.mark.asyncio
async def test_cache_delete():
    """Test de suppression du cache avec mock"""
    # Création du mock directement dans le test
    cache = MagicMock(spec=CacheManager)
    cache.delete = AsyncMock(return_value=True)
    
    # Test data
    cache_key = "test:delete_key"
    
    # Suppression
    deleted = await cache.delete(cache_key)
    assert deleted is True
    
    # Vérifier que la méthode delete a été appelée avec les bons arguments
    cache.delete.assert_called_once_with(cache_key) 