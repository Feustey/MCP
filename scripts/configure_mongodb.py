#!/usr/bin/env python3
"""
Script de configuration de MongoDB sur Hostinger
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import logging
from typing import Dict, Any, List
import json
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MongoDBConfigurator:
    def __init__(self, mongo_url: str, username: str, password: str):
        """Initialise le configurateur MongoDB."""
        self.client = MongoClient(
            mongo_url,
            username=username,
            password=password,
            serverSelectionTimeoutMS=5000
        )
        self.db = self.client.rag_db
    
    def configure_mongodb(self) -> bool:
        """Configure MongoDB avec les paramètres optimisés."""
        try:
            # Vérifier la connexion
            self.client.admin.command('ping')
            logger.info("Connexion à MongoDB établie")
            
            # Créer les collections avec validation
            self._create_collections()
            
            # Créer les index
            self._create_indexes()
            
            # Configurer les paramètres de la base de données
            self._configure_database()
            
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Erreur de connexion à MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la configuration de MongoDB: {e}")
            return False
    
    def _create_collections(self):
        """Crée les collections avec validation de schéma."""
        try:
            # Collection pour les embeddings
            self.db.create_collection(
                "embeddings",
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["text", "embedding", "model", "timestamp"],
                        "properties": {
                            "text": {"bsonType": "string"},
                            "embedding": {"bsonType": "array", "items": {"bsonType": "double"}},
                            "model": {"bsonType": "string"},
                            "timestamp": {"bsonType": "date"}
                        }
                    }
                }
            )
            logger.info("Collection 'embeddings' créée")
            
            # Collection pour les requêtes
            self.db.create_collection(
                "queries",
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["query", "response", "model", "timestamp"],
                        "properties": {
                            "query": {"bsonType": "string"},
                            "response": {"bsonType": "string"},
                            "model": {"bsonType": "string"},
                            "timestamp": {"bsonType": "date"},
                            "metadata": {"bsonType": "object"}
                        }
                    }
                }
            )
            logger.info("Collection 'queries' créée")
            
        except OperationFailure as e:
            logger.error(f"Erreur lors de la création des collections: {e}")
    
    def _create_indexes(self):
        """Crée les index nécessaires."""
        try:
            # Index pour les embeddings
            self.db.embeddings.create_index([
                ("text", "text"),
                ("model", 1),
                ("timestamp", -1)
            ])
            logger.info("Index pour 'embeddings' créé")
            
            # Index pour les requêtes
            self.db.queries.create_index([
                ("query", "text"),
                ("model", 1),
                ("timestamp", -1)
            ])
            logger.info("Index pour 'queries' créé")
            
        except OperationFailure as e:
            logger.error(f"Erreur lors de la création des index: {e}")
    
    def _configure_database(self):
        """Configure les paramètres de la base de données."""
        try:
            # Configurer les paramètres de la base de données
            self.client.admin.command({
                "setParameter": 1,
                "wiredTigerConcurrentReadTransactions": 128,
                "wiredTigerConcurrentWriteTransactions": 128
            })
            logger.info("Paramètres de la base de données configurés")
            
        except OperationFailure as e:
            logger.error(f"Erreur lors de la configuration de la base de données: {e}")
    
    def test_performance(self) -> Dict[str, Any]:
        """Teste les performances de MongoDB."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        try:
            # Test de performance pour les écritures
            start_time = datetime.now()
            for i in range(1000):
                self.db.embeddings.insert_one({
                    "text": f"Test text {i}",
                    "embedding": [0.1] * 1536,
                    "model": "test-model",
                    "timestamp": datetime.now()
                })
            duration = (datetime.now() - start_time).total_seconds()
            results["tests"]["write_embeddings"] = {
                "operations": 1000,
                "duration": duration,
                "ops_per_second": 1000 / duration
            }
            
            # Test de performance pour les lectures
            start_time = datetime.now()
            for i in range(1000):
                self.db.embeddings.find_one({"text": f"Test text {i}"})
            duration = (datetime.now() - start_time).total_seconds()
            results["tests"]["read_embeddings"] = {
                "operations": 1000,
                "duration": duration,
                "ops_per_second": 1000 / duration
            }
            
            # Nettoyer les données de test
            self.db.embeddings.delete_many({"model": "test-model"})
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors des tests de performance: {e}")
            return results

def main():
    """Fonction principale."""
    # Récupérer les variables d'environnement
    mongo_url = os.getenv("MONGODB_URL")
    username = os.getenv("MONGODB_USER")
    password = os.getenv("MONGODB_PASSWORD")
    
    if not all([mongo_url, username, password]):
        logger.error("Variables d'environnement MongoDB manquantes")
        return 1
    
    # Configurer MongoDB
    configurator = MongoDBConfigurator(mongo_url, username, password)
    if not configurator.configure_mongodb():
        return 1
    
    # Tester les performances
    results = configurator.test_performance()
    logger.info("Résultats des tests de performance:")
    logger.info(json.dumps(results, indent=2))
    
    return 0

if __name__ == "__main__":
    exit(main()) 