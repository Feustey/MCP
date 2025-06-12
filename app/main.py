# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.routes import nodes, wallet, admin, lightning_scoring, intelligence  # Ajout du routeur intelligence
from app.db import client, MONGO_DB, db # Importe le client et la db pour le shutdown
from src.utils.cache_manager import cache_manager
import uvicorn
import os
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Version avec améliorations MCP-Light
app = FastAPI(
    title="MCP Lightning Network Optimizer",
    description="API complète pour l'optimisation de nœuds Lightning avec intelligence artificielle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS pour production
cors_origins = os.getenv("CORS_ORIGINS", "https://dazno.de,https://api.dazno.de").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Middleware de sécurité pour les hosts de confiance
allowed_hosts = os.getenv("ALLOWED_HOSTS", "*").split(",")
if "*" not in allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Variable globale pour le temps de démarrage
start_time = datetime.utcnow()

@app.on_event("startup")
async def startup_event():
    """Initialisation des services au démarrage"""
    global start_time
    start_time = datetime.utcnow()
    
    # Test de connexion au cache
    try:
        await cache_manager.set("startup_test", {"started": True}, ttl=10)
        await cache_manager.delete("startup_test")
        logging.info("Cache Redis initialisé avec succès")
    except Exception as e:
        logging.warning(f"Impossible d'initialiser le cache Redis: {str(e)}")
    
    logging.info("MCP Lightning Optimizer démarré avec succès")

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage des ressources à l'arrêt"""
    try:
        # Fermeture des connexions cache
        await cache_manager.close()
        logging.info("Cache fermé proprement")
    except Exception as e:
        logging.error(f"Erreur lors de la fermeture du cache: {str(e)}")
    
    try:
        # Fermeture des connexions MongoDB
        client.close()
        logging.info("Connexion MongoDB fermée")
    except Exception as e:
        logging.error(f"Erreur lors de la fermeture MongoDB: {str(e)}")

# Inclusion des routes avec ordre d'importance
app.include_router(intelligence.router)  # Routes d'intelligence MCP prioritaires
app.include_router(nodes.router)
app.include_router(wallet.router)
app.include_router(admin.router)
app.include_router(lightning_scoring.router)

@app.get("/", tags=["Root"])
async def read_root():
    """Endpoint racine avec informations sur l'API MCP"""
    uptime = (datetime.utcnow() - start_time).total_seconds()
    
    return {
        "message": "MCP Lightning Network Optimizer API",
        "description": "API d'intelligence artificielle pour l'optimisation de nœuds Lightning Network",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "features": [
            "Analyse de nœuds Lightning via Sparkseer",
            "Recommandations IA via OpenAI",
            "Cache Redis haute performance",
            "API versionnée et documentée",
            "Métriques de performance",
            "Health checks automatiques"
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "node_info": "/api/v1/node/{pubkey}/info",
            "recommendations": "/api/v1/node/{pubkey}/recommendations", 
            "priorities": "/api/v1/node/{pubkey}/priorities",
            "bulk_analysis": "/api/v1/nodes/bulk-analysis",
            "metrics": "/api/v1/metrics",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "external_integrations": {
            "sparkseer": "Données de réseau Lightning",
            "openai": "Intelligence artificielle",
            "lnbits": "Gestion de wallet local",
            "redis": "Cache haute performance"
        },
        "status": "operational"
    }

# Permet de lancer l'app avec `python app/main.py` pour le développement
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True # Recharge automatiquement lors des modifications du code
    ) 