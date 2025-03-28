import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
import json

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

class RequestManager:
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.request_queue: List[BatchRequest] = []
        self.processing = False
        self.semaphore = asyncio.Semaphore(max_concurrent)

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
        """Traite une requête individuelle avec gestion de la concurrence."""
        async with self.semaphore:
            try:
                # Simulation du traitement de la requête
                # À remplacer par l'appel réel à l'API
                await asyncio.sleep(0.1)  # Simulation de latence
                return {
                    "endpoint": request.endpoint,
                    "params": request.params,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"Erreur lors du traitement de la requête: {str(e)}")
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