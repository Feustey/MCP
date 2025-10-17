import aiohttp
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from config.rag_config import settings as rag_settings

logger = logging.getLogger(__name__)


class OllamaClientError(Exception):
    """Exception de base pour les erreurs du client Ollama."""
    pass


class OllamaTimeoutError(OllamaClientError):
    """Exception levée en cas de timeout."""
    pass


class OllamaModelNotFoundError(OllamaClientError):
    """Exception levée quand le modèle n'est pas disponible."""
    pass


class OllamaClient:
    """Client asynchrone pour Ollama (embeddings et génération).

    Supporte streaming, retry avec backoff, et gestion d'erreurs robuste.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.base_url = (base_url or rag_settings.OLLAMA_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retourne une session réutilisable avec connection pooling optimisé."""
        if self._session is None or self._session.closed:
            # Connection pooling optimisé pour meilleures performances
            connector = aiohttp.TCPConnector(
                limit=100,                  # Pool de 100 connexions max
                limit_per_host=50,          # Max 50 par host
                ttl_dns_cache=300,          # Cache DNS 5 minutes
                keepalive_timeout=60,       # Keep-alive 60s
                enable_cleanup_closed=True, # Nettoyage auto des connexions fermées
                force_close=False           # Réutiliser les connexions
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self._session

    async def close(self):
        """Ferme la session HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def healthcheck(self) -> bool:
        """Vérifie si Ollama est accessible."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Healthcheck Ollama failed: {e}")
            return False

    async def _retry_with_backoff(self, coro, error_msg: str):
        """Exécute une coroutine avec retry et backoff exponentiel."""
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return await coro()
            except asyncio.TimeoutError as e:
                last_exception = OllamaTimeoutError(f"{error_msg}: timeout after {self.timeout}s")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    raise OllamaModelNotFoundError(f"{error_msg}: model not found (404)")
                last_exception = OllamaClientError(f"{error_msg}: HTTP {e.status}")
                if attempt < self.max_retries - 1 and e.status >= 500:
                    wait_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(f"HTTP {e.status} on attempt {attempt + 1}/{self.max_retries}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    break
            except Exception as e:
                last_exception = OllamaClientError(f"{error_msg}: {str(e)}")
                break
        
        raise last_exception or OllamaClientError(error_msg)

    async def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """Génère un embedding pour le texte donné."""
        url = f"{self.base_url}/api/embeddings"
        payload: Dict[str, Any] = {
            "model": model or rag_settings.EMBED_MODEL,
            "prompt": text,  # Ollama utilise "prompt" pour embeddings
        }

        async def _embed():
            session = await self._get_session()
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()
                # Ollama embeddings renvoient { embedding: [...] }
                embedding = data.get("embedding")
                if not embedding:
                    raise OllamaClientError("No embedding returned from Ollama")
                return embedding

        return await self._retry_with_backoff(_embed, f"Embed failed for model {payload['model']}")

    async def embed_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        """Génère des embeddings pour une liste de textes."""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text, model)
            embeddings.append(embedding)
        return embeddings

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        top_p: float = 0.9,
        stream: bool = False,
    ) -> str:
        """Génère une complétion (non-streaming)."""
        if stream:
            raise ValueError("Use generate_stream() for streaming mode")

        url = f"{self.base_url}/api/generate"
        options: Dict[str, Any] = {
            "temperature": float(temperature),
            "top_p": float(top_p),
        }
        if num_ctx:
            options["num_ctx"] = int(num_ctx)
        if max_tokens:
            options["num_predict"] = int(max_tokens)

        payload: Dict[str, Any] = {
            "model": model or rag_settings.GEN_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        async def _generate():
            session = await self._get_session()
            timeout = aiohttp.ClientTimeout(total=max(self.timeout, 90.0))
            async with session.post(url, json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                data = await resp.json()
                # Réponse: { response: "...", done: true, ... }
                response_text = data.get("response", "").strip()
                if not response_text:
                    logger.warning(f"Empty response from Ollama for prompt: {prompt[:100]}...")
                return response_text

        return await self._retry_with_backoff(_generate, f"Generate failed for model {payload['model']}")

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        num_ctx: Optional[int] = None,
        top_p: float = 0.9,
    ) -> AsyncIterator[str]:
        """Génère une complétion en mode streaming."""
        url = f"{self.base_url}/api/generate"
        options: Dict[str, Any] = {
            "temperature": float(temperature),
            "top_p": float(top_p),
        }
        if num_ctx:
            options["num_ctx"] = int(num_ctx)
        if max_tokens:
            options["num_predict"] = int(max_tokens)

        payload: Dict[str, Any] = {
            "model": model or rag_settings.GEN_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": options,
        }

        session = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=max(self.timeout, 180.0))
        
        try:
            async with session.post(url, json=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                
                # Lecture ligne par ligne du stream SSE
                async for line in resp.content:
                    if not line:
                        continue
                    
                    try:
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue
                        
                        data = json.loads(line_str)
                        if "response" in data:
                            chunk = data["response"]
                            if chunk:
                                yield chunk
                        
                        # Ollama envoie done:true à la fin
                        if data.get("done"):
                            break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode JSON line: {line_str[:100]}")
                        continue
        except asyncio.TimeoutError:
            raise OllamaTimeoutError(f"Stream timeout after {timeout.total}s")
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise OllamaModelNotFoundError(f"Model not found: {payload['model']}")
            raise OllamaClientError(f"Stream failed: HTTP {e.status}")


# Instance utilitaire réutilisable
ollama_client = OllamaClient()


