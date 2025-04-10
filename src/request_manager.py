from typing import List, Dict, Any

class PaginatedResponse:
    def __init__(self, items: List[Any], total: int, page: int, size: int):
        self.items = items
        self.total = total
        self.page = page
        self.size = size

class OptimizedRequestManager:
    def __init__(self, cache_manager, rate_limiter):
        self.cache_manager = cache_manager
        self.rate_limiter = rate_limiter

    async def handle_request(self, key: str, func, *args, **kwargs):
        if not await self.rate_limiter.check_rate_limit(key):
            raise Exception("Rate limit exceeded")
        return await func(*args, **kwargs) 