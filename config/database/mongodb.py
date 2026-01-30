"""
Configuration de la base de données MongoDB
Gestion des connexions et des collections pour api.dazno.de

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 27 mai 2025
"""

import os
import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio
from datetime import datetime

# Configuration du logging
logger = logging.getLogger("mcp.database")

# Variables d'environnement
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "mcp")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")
MONGO_REPLICA_SET = os.getenv("MONGO_REPLICA_SET")
MONGO_SSL = os.getenv("MONGO_SSL", "true").lower() == "true"
MONGO_SSL_CA_CERTS = os.getenv("MONGO_SSL_CA_CERTS")
MONGO_SSL_CERT_REQS = os.getenv("MONGO_SSL_CERT_REQS", "CERT_REQUIRED")

# Configuration de la connexion
CONNECTION_TIMEOUT = 5000  # ms
SERVER_SELECTION_TIMEOUT = 5000  # ms
MAX_POOL_SIZE = 100
MIN_POOL_SIZE = 10
MAX_IDLE_TIME = 30000  # ms
WAIT_QUEUE_TIMEOUT = 10000  # ms

class MongoDB:
    """Gestionnaire de connexion MongoDB"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self._collections = {}
        
    async def connect(self) -> bool:
        """Établit la connexion à MongoDB"""
        try:
            # Construction de l'URI
            uri = MONGO_URI
            if MONGO_USER and MONGO_PASSWORD:
                uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{uri.split('://')[1]}"
            
            # Options de connexion
            options = {
                "serverSelectionTimeoutMS": SERVER_SELECTION_TIMEOUT,
                "connectTimeoutMS": CONNECTION_TIMEOUT,
                "maxPoolSize": MAX_POOL_SIZE,
                "minPoolSize": MIN_POOL_SIZE,
                "maxIdleTimeMS": MAX_IDLE_TIME,
                "waitQueueTimeoutMS": WAIT_QUEUE_TIMEOUT,
                "authSource": MONGO_AUTH_SOURCE
            }
            
            if MONGO_REPLICA_SET:
                options["replicaSet"] = MONGO_REPLICA_SET
            
            if MONGO_SSL:
                options["ssl"] = True
                if MONGO_SSL_CA_CERTS:
                    # PyMongo 4+ : tlsCAFile remplace ssl_ca_certs
                    options["tlsCAFile"] = MONGO_SSL_CA_CERTS
                # ssl_cert_reqs supprimé : non supporté par PyMongo 4+ (utiliser tlsAllowInvalidCertificates dans l'URI si besoin)
            
            # Connexion
            self.client = AsyncIOMotorClient(uri, **options)
            self.db = self.client[MONGO_DB]
            
            # Test de connexion
            await self.client.admin.command("ping")
            logger.info("Connected to MongoDB successfully")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            return False
    
    async def disconnect(self):
        """Ferme la connexion à MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, name: str):
        """Récupère une collection"""
        if name not in self._collections:
            self._collections[name] = self.db[name]
        return self._collections[name]
    
    async def create_indexes(self):
        """Crée les index nécessaires"""
        try:
            # Index pour les utilisateurs
            users = self.get_collection("users")
            await users.create_index("email", unique=True)
            await users.create_index("tenant_id")
            
            # Index pour les nœuds
            nodes = self.get_collection("nodes")
            await nodes.create_index("node_id", unique=True)
            await nodes.create_index("tenant_id")
            await nodes.create_index("status")
            
            # Index pour les simulations
            simulations = self.get_collection("simulations")
            await simulations.create_index("simulation_id", unique=True)
            await simulations.create_index("node_id")
            await simulations.create_index("tenant_id")
            await simulations.create_index("created_at")
            
            # Index pour les optimisations
            optimizations = self.get_collection("optimizations")
            await optimizations.create_index("optimization_id", unique=True)
            await optimizations.create_index("node_id")
            await optimizations.create_index("tenant_id")
            await optimizations.create_index("created_at")
            
            logger.info("Created MongoDB indexes successfully")
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB indexes: {str(e)}")
            raise
    
    async def check_health(self) -> Dict[str, Any]:
        """Vérifie la santé de la base de données"""
        try:
            # Vérifier la connexion
            await self.client.admin.command("ping")
            
            # Vérifier les statistiques
            stats = await self.db.command("dbStats")
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": {
                    "collections": stats.get("collections", 0),
                    "objects": stats.get("objects", 0),
                    "dataSize": stats.get("dataSize", 0),
                    "storageSize": stats.get("storageSize", 0),
                    "indexes": stats.get("indexes", 0),
                    "indexSize": stats.get("indexSize", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }

# Instance globale
mongodb = MongoDB()

# Fonctions utilitaires
async def get_database():
    """Récupère l'instance de la base de données (AsyncIOMotorDatabase pour accès aux collections)."""
    if not mongodb.client:
        await mongodb.connect()
    return mongodb.db

async def get_collection(name: str):
    """Récupère une collection"""
    db = await get_database()
    return db.get_collection(name) 