from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

def configure_performance(app: FastAPI):
    """Configure performance optimizations"""
    
    # Compression GZIP
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Cache headers pour documentation statique
    @app.middleware("http")
    async def add_cache_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    # Limite de requêtes
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return app

# Configuration Uvicorn optimisée
UVICORN_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,
    "loop": "uvloop",
    "http": "httptools",
    "log_level": "warning",
    "access_log": False,
    "use_colors": False,
    "limit_concurrency": 1000,
    "limit_max_requests": 10000,
    "timeout_keep_alive": 5
}
