#!/usr/bin/env python3
"""
Testeur de charge pour le système MCP.
Ce script simule des conditions extrêmes pour tester la robustesse du système.

Dernière mise à jour: 9 mai 2025
"""

import asyncio
import aiohttp
import time
import random
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stress_tester")

# Constantes
API_URL = os.getenv("MCP_API_URL", "http://localhost:8001")
TEST_DURATION_SECONDS = int(os.getenv("TEST_DURATION_SECONDS", 60))  # 1 minute par défaut
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", 100))

# Profiles de nœuds pour les tests
NODE_PROFILES = [
    "normal", "saturated", "inactive", "abused", "star", 
    "unstable", "aggressive_fees", "routing_hub", "dead_node", "experimental"
]

class StressTester:
    """Stress tester pour MCP avec mesure de métriques de performance"""
    
    def __init__(self, api_url: str = API_URL):
        """Initialise le testeur de charge"""
        self.api_url = api_url
        self.results = []
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.session = None
        
    async def initialize(self):
        """Initialise la session HTTP"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def close(self):
        """Ferme la session HTTP"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def test_health_check(self):
        """Test de vérification de santé de l'API"""
        try:
            # Faire la requête de santé
            async with self.session.get(
                f"{self.api_url}/health"
            ) as response:
                status_code = response.status
                data = await response.json()
                
                logger.info(f"Health check: {status_code} - {data}")
                return status_code == 200
                
        except Exception as e:
            logger.error(f"Erreur lors du health check: {str(e)}")
            return False
    
    async def test_dashboard_metrics(self):
        """Test de récupération des métriques du tableau de bord"""
        try:
            # Faire la requête de métriques
            async with self.session.get(
                f"{self.api_url}/api/v1/dashboard/metrics"
            ) as response:
                status_code = response.status
                data = await response.json()
                
                logger.info(f"Dashboard metrics: {status_code} - {len(data) if isinstance(data, dict) else 0} métriques")
                return status_code == 200
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques: {str(e)}")
            return False
    
    async def test_profiles(self):
        """Test de récupération des profils de simulation"""
        try:
            # Faire la requête des profils
            async with self.session.get(
                f"{self.api_url}/api/v1/simulate/profiles"
            ) as response:
                status_code = response.status
                data = await response.json()
                
                logger.info(f"Profiles: {status_code} - {data}")
                return status_code == 200
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des profils: {str(e)}")
            return False
    
    async def run_stress_test(self, duration_seconds: int = TEST_DURATION_SECONDS):
        """
        Exécute le test de charge complet
        
        Args:
            duration_seconds: Durée du test en secondes
        """
        logger.info(f"Démarrage du test de charge ({duration_seconds}s, {REQUESTS_PER_MINUTE} req/min)...")
        
        # Initialiser la session HTTP
        await self.initialize()
        
        try:
            # Vérifier la santé de l'API
            health_ok = await self.test_health_check()
            if not health_ok:
                logger.error("L'API n'est pas en bonne santé, arrêt du test")
                return
            
            # Vérifier les métriques
            metrics_ok = await self.test_dashboard_metrics()
            if not metrics_ok:
                logger.warning("Problème avec les métriques du tableau de bord")
            
            # Vérifier les profils
            profiles_ok = await self.test_profiles()
            if not profiles_ok:
                logger.warning("Problème avec les profils de simulation")
            
            # Calculer l'intervalle entre les requêtes
            interval = 60 / REQUESTS_PER_MINUTE
            
            # Enregistrer le temps de début
            self.start_time = datetime.now()
            end_time = self.start_time + timedelta(seconds=duration_seconds)
            
            # Exécuter les requêtes jusqu'à la fin du test
            count = 0
            success_count = 0
            error_count = 0
            
            while datetime.now() < end_time:
                # Sélectionner aléatoirement un type de requête
                request_type = random.choice(["health", "metrics"])
                
                start_time = time.time()
                try:
                    if request_type == "health":
                        result = await self.test_health_check()
                    else:  # metrics
                        result = await self.test_dashboard_metrics()
                    
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Erreur lors de la requête {request_type}: {str(e)}")
                    error_count += 1
                
                count += 1
                end_time_req = time.time()
                latency = end_time_req - start_time
                
                # Attendre l'intervalle calculé entre les requêtes
                await asyncio.sleep(interval)
            
            # Enregistrer le temps de fin
            self.end_time = datetime.now()
            
            # Afficher les statistiques
            duration = (self.end_time - self.start_time).total_seconds()
            logger.info(f"Test de charge terminé en {duration:.2f}s")
            logger.info(f"Requêtes totales: {count}")
            logger.info(f"Requêtes réussies: {success_count} ({success_count/count*100:.2f}%)")
            logger.info(f"Requêtes en erreur: {error_count} ({error_count/count*100:.2f}%)")
            logger.info(f"Requêtes par seconde: {count/duration:.2f}")
            
        finally:
            # Fermer la session HTTP
            await self.close()

async def main():
    """Fonction principale"""
    logger.info("Démarrage du test de charge MCP...")
    
    tester = StressTester()
    await tester.run_stress_test()
    
    logger.info("Test de charge terminé")

if __name__ == "__main__":
    asyncio.run(main()) 