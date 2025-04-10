from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import close_mongo_connection
from src.api.automation_endpoints import router as automation_router
from src.api.rag_endpoints import router as rag_router
from src.api.network_endpoints import router as network_router
from src.api.v2.monitor.monitor_endpoints import router as monitor_router

app = FastAPI(
    title="MCP API",
    description="API pour le système MCP (Monitoring, Control, and Planning) pour Lightning Network",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(automation_router)
app.include_router(rag_router)
app.include_router(network_router)
app.include_router(monitor_router)

@app.on_event("startup")
async def startup_event():
    """Événement de démarrage de l'application"""
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """Événement d'arrêt de l'application"""
    await close_mongo_connection()

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
            "rag": "ok",
            "network": "ok",
            "automation": "ok"
        }
    }
