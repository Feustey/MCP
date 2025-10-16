"""Tests unitaires pour le client Ollama."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from src.clients.ollama_client import (
    OllamaClient,
    OllamaClientError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
)


@pytest.fixture
def ollama_client():
    """Fixture pour créer un client Ollama de test."""
    return OllamaClient(base_url="http://test-ollama:11434", timeout=10.0, max_retries=2)


@pytest.mark.asyncio
async def test_healthcheck_success(ollama_client):
    """Test du healthcheck en cas de succès."""
    mock_response = AsyncMock()
    mock_response.status = 200
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.get.return_value.__aexit__ = AsyncMock()
        
        result = await ollama_client.healthcheck()
        assert result is True


@pytest.mark.asyncio
async def test_healthcheck_failure(ollama_client):
    """Test du healthcheck en cas d'échec."""
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.get.side_effect = Exception("Connection refused")
        
        result = await ollama_client.healthcheck()
        assert result is False


@pytest.mark.asyncio
async def test_embed_success(ollama_client):
    """Test de génération d'embedding réussie."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
    mock_response.raise_for_status = Mock()
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.post.return_value.__aexit__ = AsyncMock()
        
        embedding = await ollama_client.embed("test text", model="test-model")
        assert embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_no_embedding_error(ollama_client):
    """Test d'erreur quand pas d'embedding retourné."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={})
    mock_response.raise_for_status = Mock()
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.post.return_value.__aexit__ = AsyncMock()
        
        with pytest.raises(OllamaClientError, match="No embedding returned"):
            await ollama_client.embed("test text")


@pytest.mark.asyncio
async def test_embed_batch(ollama_client):
    """Test de génération d'embeddings en batch."""
    with patch.object(ollama_client, 'embed') as mock_embed:
        mock_embed.side_effect = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]
        
        embeddings = await ollama_client.embed_batch(["text1", "text2", "text3"])
        assert len(embeddings) == 3
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[2] == [0.7, 0.8, 0.9]


@pytest.mark.asyncio
async def test_generate_success(ollama_client):
    """Test de génération de texte réussie."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"response": "Test response", "done": True})
    mock_response.raise_for_status = Mock()
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.post.return_value.__aexit__ = AsyncMock()
        
        response = await ollama_client.generate(
            prompt="Test prompt",
            model="test-model",
            temperature=0.2,
            max_tokens=100,
        )
        assert response == "Test response"


@pytest.mark.asyncio
async def test_generate_empty_response(ollama_client):
    """Test de génération avec réponse vide."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"response": "", "done": True})
    mock_response.raise_for_status = Mock()
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.post.return_value.__aexit__ = AsyncMock()
        
        response = await ollama_client.generate("Test prompt")
        assert response == ""


@pytest.mark.asyncio
async def test_generate_stream_mode_error(ollama_client):
    """Test d'erreur quand stream=True est passé à generate()."""
    with pytest.raises(ValueError, match="Use generate_stream"):
        await ollama_client.generate("test", stream=True)


@pytest.mark.asyncio
async def test_generate_stream_success(ollama_client):
    """Test de génération en streaming."""
    # Simuler un stream de réponses JSON
    mock_lines = [
        b'{"response": "Hello", "done": false}\n',
        b'{"response": " world", "done": false}\n',
        b'{"response": "!", "done": true}\n',
    ]
    
    async def mock_iter_lines():
        for line in mock_lines:
            yield line
    
    mock_response = AsyncMock()
    mock_response.content.__aiter__ = lambda self: mock_iter_lines()
    mock_response.raise_for_status = Mock()
    
    with patch.object(ollama_client, '_get_session') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock()
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.post.return_value.__aexit__ = AsyncMock()
        
        chunks = []
        async for chunk in ollama_client.generate_stream("Test prompt"):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_retry_with_backoff_timeout(ollama_client):
    """Test du mécanisme de retry en cas de timeout."""
    call_count = 0
    
    async def mock_coro():
        nonlocal call_count
        call_count += 1
        raise asyncio.TimeoutError()
    
    with pytest.raises(OllamaTimeoutError):
        await ollama_client._retry_with_backoff(mock_coro, "Test error")
    
    # Doit avoir essayé max_retries fois
    assert call_count == ollama_client.max_retries


@pytest.mark.asyncio
async def test_retry_with_backoff_404_error(ollama_client):
    """Test du mécanisme de retry en cas d'erreur 404 (pas de retry)."""
    import aiohttp
    
    call_count = 0
    
    async def mock_coro():
        nonlocal call_count
        call_count += 1
        raise aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=404,
        )
    
    with pytest.raises(OllamaModelNotFoundError):
        await ollama_client._retry_with_backoff(mock_coro, "Test error")
    
    # Ne doit avoir essayé qu'une fois (404 = pas de retry)
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_with_backoff_500_error(ollama_client):
    """Test du mécanisme de retry en cas d'erreur 5xx."""
    import aiohttp
    
    call_count = 0
    
    async def mock_coro():
        nonlocal call_count
        call_count += 1
        raise aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=500,
        )
    
    with pytest.raises(OllamaClientError):
        await ollama_client._retry_with_backoff(mock_coro, "Test error")
    
    # Doit avoir essayé max_retries fois
    assert call_count == ollama_client.max_retries


@pytest.mark.asyncio
async def test_close_session(ollama_client):
    """Test de fermeture de la session."""
    mock_session = AsyncMock()
    mock_session.closed = False
    ollama_client._session = mock_session
    
    await ollama_client.close()
    
    mock_session.close.assert_called_once()
    assert ollama_client._session is None


def test_client_initialization():
    """Test de l'initialisation du client."""
    client = OllamaClient(
        base_url="http://custom:11434",
        timeout=30.0,
        max_retries=5,
        retry_backoff=2.0,
    )
    
    assert client.base_url == "http://custom:11434"
    assert client.timeout == 30.0
    assert client.max_retries == 5
    assert client.retry_backoff == 2.0

