#!/usr/bin/env python3
"""
Morpheus - Service d'analyse et monitoring avancé
Point d'entrée principal
"""

import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
from prometheus_client import Counter, Histogram, generate_latest
import time

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("morpheus")

# Métriques Prometheus
REQUEST_COUNT = Counter('morpheus_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('morpheus_request_duration_seconds', 'Request duration')

# Application FastAPI
app = FastAPI(
    title="Morpheus",
    description="Service d'analyse et monitoring avancé pour MCP",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Page d'accueil"""
    REQUEST_COUNT.labels(method='GET', endpoint='/').inc()
    return {
        "service": "Morpheus",
        "version": "1.0.0",
        "description": "Service d'analyse et monitoring avancé pour MCP",
        "status": "running",
        "timestamp": int(time.time())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    REQUEST_COUNT.labels(method='GET', endpoint='/health').inc()
    return {
        "status": "healthy",
        "service": "morpheus",
        "timestamp": int(time.time()),
        "uptime": int(time.time() - start_time)
    }

@app.get("/metrics")
async def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest()

@app.get("/api/v1/status")
async def api_status():
    """Status de l'API"""
    REQUEST_COUNT.labels(method='GET', endpoint='/api/v1/status').inc()
    
    # Variables d'environnement pour vérifier la configuration
    config_status = {
        "mongo_configured": bool(os.getenv("MONGO_URL")),
        "redis_configured": bool(os.getenv("REDIS_URL")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "lightning_configured": bool(os.getenv("LIGHTNING_ADDRESS")),
        "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "grafana_url": os.getenv("MORPHEUS_GRAFANA_URL", "http://grafana:3000"),
        "prometheus_url": os.getenv("MORPHEUS_PROMETHEUS_URL", "http://prometheus:9090")
    }
    
    return {
        "service": "morpheus",
        "api_version": "v1",
        "status": "operational",
        "configuration": config_status,
        "timestamp": int(time.time())
    }

@app.get("/api/v1/analyze")
async def analyze_system():
    """Analyse basique du système"""
    REQUEST_COUNT.labels(method='GET', endpoint='/api/v1/analyze').inc()
    
    # Simulation d'analyse (à implémenter selon les besoins)
    analysis = {
        "system_health": "good",
        "performance_score": 85,
        "alerts": [],
        "recommendations": [
            "Système fonctionnel",
            "Monitoring actif",
            "Tous les services sont opérationnels"
        ],
        "last_check": int(time.time())
    }
    
    return analysis

# Variable globale pour l'uptime
start_time = time.time()

def main():
    """Point d'entrée principal"""
    host = os.getenv("MORPHEUS_HOST", "0.0.0.0")
    port = int(os.getenv("MORPHEUS_PORT", "8001"))
    debug = os.getenv("MORPHEUS_DEBUG", "false").lower() == "true"
    workers = int(os.getenv("MORPHEUS_WORKERS", "1"))
    
    logger.info(f"🤖 Démarrage de Morpheus sur {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Workers: {workers}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        workers=workers if not debug else 1
    )

if __name__ == "__main__":
    main()