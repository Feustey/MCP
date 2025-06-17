import httpx
import logging
from typing import List, Dict, Any, Optional
from config.rag_config import settings
from rag.cache import cached
from rag.metrics import track_metrics, track_cache_operation

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client amélioré pour Ollama avec cache et métriques."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.default_model = settings.OLLAMA_DEFAULT_MODEL
    
    async def test_connection(self) -> bool:
        """Test la connexion à Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur de connexion à Ollama: {e}")
            return False
    
    @track_metrics(metric_type='query')
    async def get_models(self) -> Dict[str, Any]:
        """Récupère la liste des modèles disponibles."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Erreur récupération modèles: {e}")
            return {"models": []}
    
    @track_metrics(metric_type='query')
    @cached(ttl=3600)  # Cache pour 1 heure
    async def generate_response(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """Génère une réponse via Ollama avec cache."""
        model = model or self.default_model
        try:
            url = f"{self.base_url}/api/generate"
            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Erreur génération: {e}")
            raise
    
    @track_metrics(metric_type='embedding')
    @cached(ttl=3600)  # Cache pour 1 heure
    async def get_embedding(
        self,
        text: str,
        model: str = None
    ) -> List[float]:
        """Génère un embedding via Ollama avec cache."""
        model = model or self.default_model
        try:
            url = f"{self.base_url}/api/embeddings"
            data = {
                "model": model,
                "prompt": text
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()
                result = response.json()
                return result.get("embedding", [])
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            raise
    
    @track_metrics(metric_type='query')
    async def batch_get_embeddings(
        self,
        texts: List[str],
        model: str = None,
        batch_size: int = 10
    ) -> List[List[float]]:
        """Génère des embeddings en batch pour optimiser les performances."""
        model = model or self.default_model
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            tasks = [self.get_embedding(text, model) for text in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Erreur dans le batch: {result}")
                    results.append([])
                else:
                    results.append(result)
        
        return results 