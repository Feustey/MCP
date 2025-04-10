import pytest
from datetime import datetime, timedelta
from src.rag_data_provider import RAGDataProvider
from unittest.mock import Mock, patch
import asyncio

@pytest.fixture
def data_provider():
    return RAGDataProvider()

@pytest.mark.asyncio
async def test_context_retrieval(data_provider):
    """Test de récupération du contexte"""
    with patch('data_aggregator.DataAggregator.aggregate_data') as mock_aggregate:
        # Configuration du mock
        mock_aggregate.return_value = {
            "network_summary": {"total_capacity": 1000000},
            "centralities": {"nodes": [{"id": "test"}]},
            "lnbits_wallets": [{"id": "wallet1"}]
        }
        
        # Test de la récupération
        context = await data_provider.get_context_data("test query")
        
        # Vérifications
        assert "network_metrics" in context
        assert "node_data" in context
        assert "wallet_data" in context
        assert "timestamp" in context
        
        # Vérification du cache
        cached_context = await data_provider.get_context_data("test query")
        assert cached_context == context

@pytest.mark.asyncio
async def test_cache_expiration(data_provider):
    """Test d'expiration du cache"""
    # Forcer une expiration rapide
    data_provider.cache_ttl = timedelta(seconds=1)
    
    with patch('data_aggregator.DataAggregator.aggregate_data') as mock_aggregate:
        # Premier appel
        mock_aggregate.return_value = {"test": "data1"}
        context1 = await data_provider.get_context_data("test query")
        
        # Attendre l'expiration
        await asyncio.sleep(1.1)
        
        # Deuxième appel avec données différentes
        mock_aggregate.return_value = {"test": "data2"}
        context2 = await data_provider.get_context_data("test query")
        
        # Vérifier que les données sont différentes
        assert context1 != context2

@pytest.mark.asyncio
async def test_error_handling(data_provider):
    """Test de gestion des erreurs"""
    with patch('data_aggregator.DataAggregator.aggregate_data') as mock_aggregate:
        # Simuler une erreur
        mock_aggregate.side_effect = Exception("Test error")
        
        # La fonction devrait retourner un dictionnaire vide en cas d'erreur
        context = await data_provider.get_context_data("test query")
        assert context == {} 