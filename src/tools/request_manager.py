import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BatchRequest:
    """Classe pour représenter une requête en batch."""
    endpoint: str
    params: Dict[str, Any]
    priority: int = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

def get_headers() -> Dict[str, str]:
    """Get headers with API key for Sparkseer API."""
    api_key = os.getenv('SPARKSEER_API_KEY')
    if not api_key:
        raise ValueError("SPARKSEER_API_KEY not found in environment variables")
    return {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }

def validate_sparkseer_response(data: Dict[str, Any]) -> bool:
    """Valide la structure de la réponse de l'API Sparkseer."""
    required_fields = ["status", "data"]
    if not all(field in data for field in required_fields):
        logger.error(f"Réponse invalide: champs requis manquants. Données reçues: {data}")
        return False
    return True

class RequestManager:
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5, max_retries: int = 3):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.request_queue: List[BatchRequest] = []
        self.processing = False
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_url = "https://api.sparkseer.com"

    async def add_request(self, endpoint: str, params: Dict[str, Any], priority: int = 0) -> None:
        """Ajoute une requête à la file d'attente."""
        request = BatchRequest(endpoint=endpoint, params=params, priority=priority)
        self.request_queue.append(request)
        self.request_queue.sort(key=lambda x: (-x.priority, x.created_at))
        
        if not self.processing:
            asyncio.create_task(self.process_queue())

    async def process_queue(self) -> None:
        """Traite la file d'attente des requêtes."""
        self.processing = True
        while self.request_queue:
            batch = self.request_queue[:self.batch_size]
            self.request_queue = self.request_queue[self.batch_size:]
            
            tasks = []
            for request in batch:
                task = asyncio.create_task(
                    self._process_request(request)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        self.processing = False

    async def _process_request(self, request: BatchRequest) -> Any:
        """Traite une requête individuelle avec gestion de la concurrence et retries."""
        for attempt in range(self.max_retries):
            async with self.semaphore:
                try:
                    async with aiohttp.ClientSession() as session:
                        url = f"{self.base_url}{request.endpoint}"
                        async with session.get(
                            url,
                            params=request.params,
                            headers=get_headers(),
                            timeout=10 * (attempt + 1)  # Augmentation du timeout à chaque tentative
                        ) as response:
                            if response.status == 429:  # Rate limit
                                retry_after = int(response.headers.get('Retry-After', 5))
                                logger.warning(f"Rate limit atteint, attente de {retry_after}s...")
                                await asyncio.sleep(retry_after)
                                continue
                                
                            response.raise_for_status()
                            data = await response.json()
                            
                            if not validate_sparkseer_response(data):
                                logger.error(f"Réponse invalide de l'API pour l'endpoint {request.endpoint}")
                                if attempt < self.max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
                                    continue
                                return None
                                
                            return data
                except aiohttp.ClientError as e:
                    logger.error(f"Erreur réseau lors de la requête {request.endpoint} (tentative {attempt + 1}/{self.max_retries}): {str(e)}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                except asyncio.TimeoutError:
                    logger.error(f"Timeout lors de la requête {request.endpoint} (tentative {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                except Exception as e:
                    logger.error(f"Erreur inattendue lors de la requête {request.endpoint}: {str(e)}")
                    return None
        
        logger.error(f"Échec de la requête {request.endpoint} après {self.max_retries} tentatives")
        return None

class PaginatedResponse:
    def __init__(self, items: List[Any], total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = (total + page_size - 1) // page_size

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.page < self.total_pages,
            "has_previous": self.page > 1
        }

class OptimizedRequestManager:
    def __init__(self, cache_manager, rate_limiter):
        self.cache = cache_manager
        self.rate_limiter = rate_limiter
        self.request_manager = RequestManager()
        self.batch_requests: Dict[str, List[BatchRequest]] = {}

    async def make_request(self, method: str, url: str, timeout: int = 10) -> Any:
        """Effectue une requête HTTP avec cache et rate limiting."""
        cache_key = f"{method}:{url}"
        
        # Vérification du cache
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=get_headers(),
                    timeout=timeout
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if not validate_sparkseer_response(data):
                        logger.error(f"Réponse invalide de l'API pour l'URL {url}")
                        return None
                    
                    # Mise en cache de la réponse
                    await self.cache.set(cache_key, json.dumps(data))
                    return data
                    
        except aiohttp.ClientError as e:
            logger.error(f"Erreur réseau lors de la requête {url}: {str(e)}")
            return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout lors de la requête {url}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la requête {url}: {str(e)}")
            return None

    async def parallel_fetch(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Exécute plusieurs requêtes en parallèle."""
        tasks = []
        for req in requests:
            task = asyncio.create_task(
                self._fetch_with_cache(
                    req['endpoint'],
                    req['params'],
                    req.get('priority', 0)
                )
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)

    async def _fetch_with_cache(self, endpoint: str, params: Dict[str, Any], priority: int = 0) -> Any:
        """Récupère des données avec cache et rate limiting."""
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        
        # Vérification du cache
        cached_data = await self.cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Ajout à la file d'attente
        await self.request_manager.add_request(endpoint, params, priority)
        
        # Simulation de la récupération des données
        # À remplacer par l'appel réel à l'API
        data = await self.request_manager._process_request(
            BatchRequest(endpoint=endpoint, params=params)
        )
        
        if data:
            await self.cache.set(cache_key, data)
        
        return data

    async def batch_process(self, batch_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Traite un lot de requêtes."""
        self.batch_requests[batch_id] = [
            BatchRequest(**req) for req in requests
        ]
        
        results = await self.parallel_fetch(requests)
        
        return {
            "batch_id": batch_id,
            "status": "completed",
            "results": results,
            "processed_at": datetime.now().isoformat()
        }

    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut d'un lot de requêtes."""
        if batch_id not in self.batch_requests:
            return None
        
        return {
            "batch_id": batch_id,
            "total_requests": len(self.batch_requests[batch_id]),
            "processed": len(self.batch_requests[batch_id]),
            "status": "processing"
        }

    def paginate_results(self, items: List[Any], page: int, page_size: int) -> PaginatedResponse:
        """Pagine les résultats."""
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = items[start_idx:end_idx]
        
        return PaginatedResponse(
            items=paginated_items,
            total=len(items),
            page=page,
            page_size=page_size
        ) 