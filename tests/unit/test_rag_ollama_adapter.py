"""Tests unitaires pour l'adaptateur RAG Ollama."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.rag_ollama_adapter import OllamaRAGAdapter
from src.clients.ollama_client import OllamaClientError


@pytest.fixture
def adapter():
    """Fixture pour créer un adaptateur de test."""
    return OllamaRAGAdapter(
        embed_model="test-embed",
        gen_model="test-gen",
        dimension=768,
        num_ctx=4096,
        fallback_model="test-fallback",
    )


def test_adapter_initialization():
    """Test de l'initialisation de l'adaptateur."""
    adapter = OllamaRAGAdapter(
        embed_model="custom-embed",
        gen_model="custom-gen",
        dimension=1536,
        num_ctx=8192,
    )
    
    assert adapter.embed_model == "custom-embed"
    assert adapter.gen_model == "custom-gen"
    assert adapter.dimension == 1536
    assert adapter.num_ctx == 8192


def test_format_prompt_basic(adapter):
    """Test du formatage de prompt basique."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]
    
    prompt = adapter._format_prompt(messages, lang="en")
    
    assert "<|system|>" in prompt
    assert "You are a helpful assistant." in prompt
    assert "<|user|>" in prompt
    assert "What is the capital of France?" in prompt
    assert "<|assistant|>" in prompt


def test_format_prompt_multiple_messages(adapter):
    """Test du formatage avec plusieurs messages."""
    messages = [
        {"role": "system", "content": "System instruction 1"},
        {"role": "system", "content": "System instruction 2"},
        {"role": "user", "content": "User question 1"},
        {"role": "user", "content": "User question 2"},
    ]
    
    prompt = adapter._format_prompt(messages)
    
    assert "System instruction 1" in prompt
    assert "System instruction 2" in prompt
    assert "User question 1" in prompt
    assert "User question 2" in prompt


def test_format_prompt_no_system(adapter):
    """Test du formatage sans message système."""
    messages = [
        {"role": "user", "content": "Just a user question"},
    ]
    
    prompt = adapter._format_prompt(messages)
    
    assert "<|system|>" not in prompt
    assert "<|user|>" in prompt
    assert "Just a user question" in prompt


@pytest.mark.asyncio
async def test_get_embedding_async(adapter):
    """Test de génération d'embedding async."""
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        embedding = await adapter.get_embedding_async("test text")
        
        assert embedding == [0.1, 0.2, 0.3]
        mock_client.embed.assert_called_once_with("test text", adapter.embed_model)


@pytest.mark.asyncio
async def test_get_embeddings_batch_async(adapter):
    """Test de génération d'embeddings en batch."""
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.embed_batch = AsyncMock(return_value=[
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ])
        
        embeddings = await adapter.get_embeddings_batch_async(["text1", "text2"])
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]


@pytest.mark.asyncio
async def test_generate_completion_async_success(adapter):
    """Test de génération de complétion async réussie."""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hello"},
    ]
    
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.generate = AsyncMock(return_value="Hello! How can I help?")
        
        response = await adapter.generate_completion_async(
            messages=messages,
            temperature=0.2,
            max_tokens=100,
            lang="en",
        )
        
        assert "Hello" in response
        mock_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_completion_async_with_fallback(adapter):
    """Test de génération avec fallback en cas d'erreur."""
    messages = [
        {"role": "user", "content": "Test question"},
    ]
    
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        # Premier appel échoue, deuxième (fallback) réussit
        mock_client.generate = AsyncMock(side_effect=[
            OllamaClientError("Model error"),
            "Fallback response",
        ])
        
        response = await adapter.generate_completion_async(messages)
        
        assert "Fallback response" in response
        assert "mode dégradé" in response
        assert mock_client.generate.call_count == 2


@pytest.mark.asyncio
async def test_generate_completion_stream(adapter):
    """Test de génération en streaming."""
    messages = [
        {"role": "user", "content": "Count to 3"},
    ]
    
    async def mock_stream():
        for chunk in ["One", " two", " three"]:
            yield chunk
    
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.generate_stream = AsyncMock(return_value=mock_stream())
        
        chunks = []
        async for chunk in adapter.generate_completion_stream(messages):
            chunks.append(chunk)
        
        assert chunks == ["One", " two", " three"]


def test_clean_response(adapter):
    """Test du nettoyage de réponse."""
    # Réponse avec tags Llama
    response = "<|assistant|>This is a test<|end|> with   extra spaces"
    cleaned = adapter._clean_response(response)
    
    assert "<|assistant|>" not in cleaned
    assert "<|end|>" not in cleaned
    assert "  " not in cleaned  # Pas de doubles espaces
    assert cleaned == "This is a test with extra spaces"


def test_clean_response_empty(adapter):
    """Test du nettoyage d'une réponse vide."""
    cleaned = adapter._clean_response("   ")
    assert cleaned == ""


def test_map_to_rag_response(adapter):
    """Test du mapping vers le format RAG."""
    sources = [
        {"uid": "doc1", "score": 0.95},
        {"uid": "doc2", "score": 0.87},
    ]
    
    response = adapter.map_to_rag_response(
        answer="Test answer",
        sources=sources,
        confidence=0.9,
        degraded=False,
    )
    
    assert response["answer"] == "Test answer"
    assert response["sources"] == sources
    assert response["confidence"] == 0.9
    assert response["degraded"] is False
    assert response["model"] == adapter.gen_model
    assert response["embed_model"] == adapter.embed_model


def test_map_to_rag_response_degraded(adapter):
    """Test du mapping avec mode dégradé."""
    response = adapter.map_to_rag_response(
        answer="Fallback answer",
        sources=[],
        degraded=True,
    )
    
    assert response["degraded"] is True
    assert response["model"] == adapter.fallback_model


def test_get_embedding_sync(adapter):
    """Test de génération d'embedding sync (compatibilité)."""
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        # Note: Ce test peut nécessiter un event loop actif
        # Dans un vrai test, on pourrait avoir besoin d'utiliser asyncio.run
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.is_running.return_value = False
            mock_loop.return_value.run_until_complete.return_value = [0.1, 0.2, 0.3]
            
            embedding = adapter.get_embedding("test text")
            assert embedding == [0.1, 0.2, 0.3]


def test_generate_completion_sync(adapter):
    """Test de génération sync (compatibilité)."""
    messages = [{"role": "user", "content": "test"}]
    
    with patch('src.rag_ollama_adapter.ollama_client') as mock_client:
        mock_client.generate = AsyncMock(return_value="Test response")
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.is_running.return_value = False
            mock_loop.return_value.run_until_complete.return_value = "Test response"
            
            response = adapter.generate_completion(messages)
            assert "Test response" in response

