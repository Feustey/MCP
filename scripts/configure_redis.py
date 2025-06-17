#!/usr/bin/env python3
"""
Script de configuration de Redis sur Hostinger
"""

import redis
import logging
from typing import Dict, Any
import json
import os
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedisConfigurator:
    def __init__(self, redis_url: str):
        """Initialise le configurateur Redis."""
        self.redis = redis.from_url(redis_url)
        self.config: Dict[str, Any] = {
            "maxmemory": "2gb",
            "maxmemory-policy": "allkeys-lru",
            "appendonly": "yes",
            "appendfsync": "everysec",
            "save": "900 1 300 10 60 10000",
            "timeout": "300",
            "tcp-keepalive": "300"
        }
    
    def configure_redis(self) -> bool:
        """Configure Redis avec les paramètres optimisés."""
        try:
            # Vérifier la connexion
            self.redis.ping()
            logger.info("Connexion à Redis établie")
            
            # Configurer les paramètres
            for key, value in self.config.items():
                self.redis.config_set(key, value)
                logger.info(f"Configuration {key} = {value}")
            
            # Sauvegarder la configuration
            self.redis.config_rewrite()
            logger.info("Configuration Redis sauvegardée")
            
            # Créer les index pour les collections principales
            self._create_indexes()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration de Redis: {e}")
            return False
    
    def _create_indexes(self):
        """Crée les index nécessaires pour les collections principales."""
        try:
            # Index pour les embeddings
            self.redis.execute_command(
                "FT.CREATE", "idx:embeddings",
                "ON", "HASH",
                "PREFIX", "1", "embedding:",
                "SCHEMA",
                "text", "TEXT", "WEIGHT", "5.0",
                "model", "TAG",
                "timestamp", "NUMERIC", "SORTABLE"
            )
            logger.info("Index pour les embeddings créé")
            
            # Index pour les requêtes
            self.redis.execute_command(
                "FT.CREATE", "idx:queries",
                "ON", "HASH",
                "PREFIX", "1", "query:",
                "SCHEMA",
                "query", "TEXT", "WEIGHT", "5.0",
                "model", "TAG",
                "timestamp", "NUMERIC", "SORTABLE"
            )
            logger.info("Index pour les requêtes créé")
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des index: {e}")
    
    def test_performance(self) -> Dict[str, Any]:
        """Teste les performances de Redis."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        try:
            # Test de performance pour les embeddings
            start_time = datetime.now()
            for i in range(1000):
                self.redis.set(f"test:embedding:{i}", "x" * 1000)
            duration = (datetime.now() - start_time).total_seconds()
            results["tests"]["write_embeddings"] = {
                "operations": 1000,
                "duration": duration,
                "ops_per_second": 1000 / duration
            }
            
            # Test de performance pour les lectures
            start_time = datetime.now()
            for i in range(1000):
                self.redis.get(f"test:embedding:{i}")
            duration = (datetime.now() - start_time).total_seconds()
            results["tests"]["read_embeddings"] = {
                "operations": 1000,
                "duration": duration,
                "ops_per_second": 1000 / duration
            }
            
            # Nettoyer les données de test
            for i in range(1000):
                self.redis.delete(f"test:embedding:{i}")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors des tests de performance: {e}")
            return results

def main():
    """Fonction principale."""
    # Récupérer l'URL Redis depuis les variables d'environnement
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.error("REDIS_URL non définie")
        return 1
    
    # Configurer Redis
    configurator = RedisConfigurator(redis_url)
    if not configurator.configure_redis():
        return 1
    
    # Tester les performances
    results = configurator.test_performance()
    logger.info("Résultats des tests de performance:")
    logger.info(json.dumps(results, indent=2))
    
    return 0

if __name__ == "__main__":
    exit(main()) 