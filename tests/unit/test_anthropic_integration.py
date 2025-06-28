#!/usr/bin/env python3
# test_anthropic_integration.py

import os
import pytest
import json
from unittest.mock import Mock, patch
from rag.integrations.anthropic_integration import AnthropicIntegration

@pytest.fixture
def mock_anthropic_client():
    """Fixture pour mocker le client Anthropic"""
    with patch('anthropic.Anthropic') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_node_data():
    """Fixture pour les données de test d'un nœud"""
    return {
        "alias": "test_node",
        "pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
        "channels": [
            {"capacity": 1000000, "remote_pubkey": "peer1"},
            {"capacity": 2000000, "remote_pubkey": "peer2"}
        ],
        "metrics": {
            "centrality": {
                "betweenness": 0.45,
                "closeness": 0.67
            }
        },
        "fees": {
            "in": {"base": 1000, "rate": 0.0001},
            "out": {"base": 1000, "rate": 0.0001}
        }
    }

@pytest.fixture
def sample_market_data():
    """Fixture pour les données de test du marché"""
    return {
        "total_capacity": 100000000000,
        "total_channels": 50000,
        "total_nodes": 20000,
        "average_fee_rate": 0.0002,
        "timestamp": "2025-05-09T12:00:00"
    }

def test_anthropic_integration_initialization():
    """Test l'initialisation de l'intégration Anthropic"""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        assert integration.api_key == 'test_key'
        assert integration.model == "claude-opus-4-20250514"

def test_anthropic_integration_initialization_without_key():
    """Test l'initialisation sans clé API"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            AnthropicIntegration()
        assert "La clé API Anthropic est requise" in str(exc_info.value)

@pytest.mark.asyncio
async def test_generate_node_analysis(mock_anthropic_client, sample_node_data):
    """Test la génération d'analyse de nœud"""
    # Configuration du mock
    mock_response = Mock()
    mock_response.content = [{"text": "Analyse du nœud test_node"}]
    mock_anthropic_client.messages.create.return_value = mock_response

    # Test
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        result = await integration.generate_node_analysis(sample_node_data)

    # Vérifications
    assert result == "Analyse du nœud test_node"
    mock_anthropic_client.messages.create.assert_called_once()
    call_args = mock_anthropic_client.messages.create.call_args[1]
    assert call_args["model"] == "claude-opus-4-20250514"
    assert call_args["max_tokens"] == 4000
    assert call_args["temperature"] == 0.7
    assert "expert en analyse de nœuds Lightning Network" in call_args["system"]

@pytest.mark.asyncio
async def test_generate_market_analysis(mock_anthropic_client, sample_market_data):
    """Test la génération d'analyse de marché"""
    # Configuration du mock
    mock_response = Mock()
    mock_response.content = [{"text": "Analyse du marché Lightning Network"}]
    mock_anthropic_client.messages.create.return_value = mock_response

    # Test
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        result = await integration.generate_market_analysis(sample_market_data)

    # Vérifications
    assert result == "Analyse du marché Lightning Network"
    mock_anthropic_client.messages.create.assert_called_once()
    call_args = mock_anthropic_client.messages.create.call_args[1]
    assert "expert en analyse du marché Lightning Network" in call_args["system"]

@pytest.mark.asyncio
async def test_generate_recommendations(mock_anthropic_client, sample_node_data, sample_market_data):
    """Test la génération de recommandations"""
    # Configuration du mock
    mock_response = Mock()
    mock_response.content = [{"text": "Recommandations pour le nœud"}]
    mock_anthropic_client.messages.create.return_value = mock_response

    # Test
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        result = await integration.generate_recommendations(sample_node_data, sample_market_data)

    # Vérifications
    assert result == "Recommandations pour le nœud"
    mock_anthropic_client.messages.create.assert_called_once()
    call_args = mock_anthropic_client.messages.create.call_args[1]
    assert "expert en optimisation de nœuds Lightning Network" in call_args["system"]

def test_set_model():
    """Test le changement de modèle"""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        integration.set_model("claude-3-sonnet-20240229")
        assert integration.model == "claude-3-sonnet-20240229"

def test_str_representation():
    """Test la représentation string de l'intégration"""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'}):
        integration = AnthropicIntegration()
        assert str(integration) == "AnthropicIntegration(model=claude-opus-4-20250514)" 