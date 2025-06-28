#!/usr/bin/env python3
"""
Script pour lancer le système RAG MCP avec Ollama en local
Dernière mise à jour: 25 mai 2025
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
import uvicorn
from prometheus_client import start_http_server
from config.rag_config import settings

# Ajouter le répertoire du projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration du logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT
)
logger = logging.getLogger(__name__)

async def check_dependencies():
    """Vérifie que toutes les dépendances sont disponibles."""
    try:
        import redis
        import motor
        import prometheus_client
        return True
    except ImportError as e:
        logger.error(f"Dépendance manquante: {e}")
        return False

async def start_metrics_server():
    """Démarre le serveur de métriques Prometheus."""
    if settings.ENABLE_METRICS:
        try:
            start_http_server(settings.METRICS_PORT)
            logger.info(f"Serveur de métriques démarré sur le port {settings.METRICS_PORT}")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du serveur de métriques: {e}")

async def check_services():
    """Vérifie que tous les services nécessaires sont disponibles."""
    from rag.ollama_client import OllamaClient
    from rag.cache import RedisCache
    
    # Vérifier Ollama
    ollama_client = OllamaClient()
    ollama_status = await ollama_client.test_connection()
    if not ollama_status:
        logger.error("Ollama n'est pas accessible")
        return False
    
    # Vérifier Redis
    try:
        cache = RedisCache()
        await cache.redis.ping()
        logger.info("Redis est accessible")
    except Exception as e:
        logger.error(f"Redis n'est pas accessible: {e}")
        return False
    
    return True

async def main():
    """Fonction principale."""
    print("🚀 Démarrage du système RAG MCP avec Ollama")
    print("=" * 50)
    
    # Vérifier les dépendances
    if not await check_dependencies():
        print("❌ Dépendances manquantes")
        return 1
    
    # Vérifier les services
    if not await check_services():
        print("❌ Services non disponibles")
        return 1
    
    # Démarrer le serveur de métriques
    await start_metrics_server()
    
    # Démarrer l'API
    print("✅ Tous les services sont prêts")
    print("🌐 API disponible sur: http://localhost:8000")
    print("📊 Métriques disponibles sur: http://localhost:9090")
    print("📚 Documentation disponible sur: http://localhost:8000/docs")
    
    uvicorn.run(
        "rag_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main())) 