from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MCP API",
    description="API pour le système MCP (Monitoring, Control, and Planning) pour Lightning Network",
    version="1.0.0"
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
