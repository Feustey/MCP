import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock
from src.llm_selector import get_llm, OllamaLLM, ask_llm_choice

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture pour simuler les variables d'environnement."""
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://test-ollama:11434')

def test_ask_llm_choice_valid_input():
    """Test de la fonction ask_llm_choice avec une entrée valide"""
    with patch('builtins.input', return_value='ollama'):
        assert ask_llm_choice() == 'ollama'
    
    with patch('builtins.input', return_value='openai'):
        assert ask_llm_choice() == 'openai'

def test_ask_llm_choice_invalid_input():
    """Test de la fonction ask_llm_choice avec une entrée invalide"""
    with patch('builtins.input', return_value='invalid'):
        with patch('builtins.print') as mock_print:
            assert ask_llm_choice() == 'openai'
            mock_print.assert_called_once()

def test_ask_llm_choice_exception():
    """Test de la fonction ask_llm_choice avec une exception"""
    with patch('builtins.input', side_effect=Exception('Test exception')):
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            assert ask_llm_choice() == 'ollama'

def test_get_llm():
    """Test de la fonction get_llm"""
    # Test avec ollama
    llm = get_llm(llm_type="ollama", model="llama3")
    assert isinstance(llm, OllamaLLM)
    assert llm.model == "llama3"
    
    # Test avec un type non supporté
    with pytest.raises(ValueError):
        get_llm(llm_type="unsupported")

@pytest.mark.asyncio
async def test_ollama_llm_init(mock_env_vars):
    """Test de l'initialisation de OllamaLLM"""
    llm = OllamaLLM(model="llama3", temperature=0.5)
    assert llm.model == "llama3"
    assert llm.base_url == "http://test-ollama:11434"
    assert llm.model_params["temperature"] == 0.5

@pytest.mark.asyncio
async def test_ollama_llm_generate_success():
    """Test de la méthode generate avec succès"""
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(return_value={"response": "Test response"})
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        llm = OllamaLLM(model="llama3")
        result = await llm.generate("Test prompt")
        
        assert result["text"] == "Test response"
        assert result["model"] == "llama3"
        assert result["success"] is True

@pytest.mark.asyncio
async def test_ollama_llm_generate_failure():
    """Test de la méthode generate avec échec"""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Test exception"))
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            llm = OllamaLLM(model="llama3", max_retries=2)
            result = await llm.generate("Test prompt")
            
            assert "Je n'ai pas pu générer de réponse" in result["text"]
            assert result["success"] is False
            assert "Test exception" in result["error"]
            assert mock_sleep.call_count == 1  # Un retry = un sleep

@pytest.mark.asyncio
async def test_ollama_llm_acomplete():
    """Test de la méthode acomplete"""
    llm = OllamaLLM(model="llama3")
    llm.generate = AsyncMock(return_value={"text": "Test completion", "model": "llama3", "success": True})
    
    result = await llm.acomplete("System prompt", "User prompt")
    assert result.text == "Test completion"
    llm.generate.assert_called_once_with("System prompt\n\nUser prompt")

@pytest.mark.asyncio
async def test_ollama_llm_get_embedding_success():
    """Test de la méthode get_embedding avec succès"""
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        llm = OllamaLLM(model="llama3")
        result = await llm.get_embedding("Test text")
        
        assert result == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_ollama_llm_get_embedding_failure():
    """Test de la méthode get_embedding avec échec"""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Test exception"))
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('numpy.zeros', return_value=[0.0] * 384):
                llm = OllamaLLM(model="llama3")
                result = await llm.get_embedding("Test text", max_retries=1)
                
                assert len(result) == 384
                assert all(x == 0.0 for x in result) 