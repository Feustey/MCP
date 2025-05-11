#!/usr/bin/env python3
"""
Serveur FastAPI pour MCP (Moniteur et Contrôleur de Performance)
Permet de démarrer l'API avec Uvicorn.

Dernière mise à jour: 9 mai 2025
"""

import os
import sys
import uvicorn
from src.api.main import app
import logging

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

if __name__ == "__main__":
    # Créer les répertoires nécessaires
    os.makedirs("logs", exist_ok=True)
    
    # Afficher explicitement le port
    print(f">>>>>> Démarrage du serveur MCP sur {HOST}:{PORT}")
    logger.info(f"Démarrage du serveur MCP sur {HOST}:{PORT}")
    
    # Forcer le port directement
    sys.argv = ["uvicorn", "src.api.main:app", "--host", HOST, "--port", str(PORT)]
    
    # Lancement du serveur
    uvicorn.run(
        "src.api.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD
    ) 