class RateLimiter:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.rate_limit = 100  # requêtes par minute
        self.window = 60  # secondes

    async def check_rate_limit(self, key: str) -> bool:
        count = await self.cache_manager.get(key) or 0
        if count >= self.rate_limit:
            return False
        await self.cache_manager.set(key, count + 1)
        return True 