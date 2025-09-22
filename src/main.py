from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import de la configuration Swagger
try:
    from docs.api_documentation import SWAGGER_CONFIG, API_TAGS_METADATA, ERROR_RESPONSES
    swagger_config = SWAGGER_CONFIG
    openapi_tags = API_TAGS_METADATA
except ImportError:
    swagger_config = {
        "title": "MCP Lightning Network API",
        "description": "API complète pour l'analyse et la gestion des nœuds Lightning Network avec métriques avancées",
        "version": "2.0.0"
    }
    openapi_tags = None

app = FastAPI(
    **swagger_config,
    openapi_tags=openapi_tags,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.token-for-good.com",
        "https://token-for-good.com",
        "https://app.dazno.de",
        "https://dazno.de"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Middleware de sécurité basique (sans dépendances externes)
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "MCP API is running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé"""
    return {
        "status": "healthy",
        "services": {
            "api": "ok"
        }
    }

@app.get("/api/v1/health")
async def health_check_v1():
    """Endpoint de vérification de santé API v1"""
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/v1/status")
async def status_check():
    """Endpoint de statut API"""
    return {"status": "online", "endpoints": 6}

@app.get("/api/v1/metrics")
async def metrics_check():
    """Endpoint de métriques basique"""
    return {
        "cpu": "N/A",
        "memory": "N/A", 
        "disk": "N/A",
        "timestamp": "2025-08-06T07:30:00"
    }

@app.get("/api/v1/automation")
async def automation_status():
    """Endpoint automation basique"""
    return {"status": "available", "features": ["monitoring", "alerts"]}

@app.get("/api/v1/rag")
async def rag_status():
    """Endpoint RAG basique"""
    return {"status": "available", "features": ["query", "search"]}

# Import et inclusion des routes avancées
try:
    from app.routes.advanced_analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Advanced Analytics"])
    print("✅ Routes d'analyse avancées chargées")
except ImportError as e:
    print(f"⚠️ Échec chargement routes analytics: {e}")

try:
    from app.routes.lightning import router as lightning_router
    app.include_router(lightning_router, prefix="/api/v1/lightning", tags=["Lightning Network"])
    print("✅ Routes Lightning Network chargées")
except ImportError as e:
    print(f"⚠️ Échec chargement routes lightning: {e}")

try:
    from app.routes.health import router as health_router
    app.include_router(health_router, prefix="/api/v1", tags=["System Health"])
    print("✅ Routes de santé système chargées")
except ImportError as e:
    print(f"⚠️ Échec chargement routes health: {e}")

@app.on_event("startup")
async def startup_event():
    """Événements de démarrage"""
    print("🚀 MCP Lightning Network API v2.0.0 démarrée")
    print("📊 Fonctionnalités avancées:")
    print("   - Max Flow Analysis")
    print("   - Graph Theory Metrics")  
    print("   - Financial Analysis")
    print("   - Fee Optimization")
    print("   - Liquidity Management")

@app.on_event("shutdown")
async def shutdown_event():
    """Événements d'arrêt"""
    print("🛑 MCP Lightning Network API arrêtée")
