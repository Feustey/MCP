#!/usr/bin/env python3
"""
Serveur FastAPI pour MCP (Moniteur et Contrôleur de Performance)
Point d'entrée pour lancer l'API avec Uvicorn.

Dernière mise à jour: 9 mai 2025
"""

import os
import sys
import logging

# Création du dossier de logs si nécessaire
os.makedirs("logs", exist_ok=True)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp-server")

# Paramètres du serveur
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8001))
RELOAD = os.getenv("RELOAD", "false").lower() == "true"

# Import de l'application FastAPI avec gestion d'erreur explicite
try:
    from src.api.main import app
except ModuleNotFoundError as e:
    logger.error("Impossible d'importer src.api.main:app. Vérifiez la structure du projet et l'environnement PYTHONPATH.")
    print("[ERREUR IMPORT] src.api.main:app introuvable. Assurez-vous que le dossier src/ est bien présent et accessible.")
    sys.exit(1)

import uvicorn

if __name__ == "__main__":
    print(f"\n>>>>>> Démarrage du serveur MCP sur {HOST}:{PORT}\n")
    logger.info(f"Démarrage du serveur MCP sur {HOST}:{PORT}")

    # Lancement du serveur Uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD
    ) 