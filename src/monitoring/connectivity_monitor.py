#!/usr/bin/env python3
"""
Module de surveillance de la connectivité externe pour MCP.
Surveille l'état des services externes critiques.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """États possibles d'un service."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"

class ServiceHealth:
    """Représente la santé d'un service externe."""
    
    def __init__(self, name: str, url: str, critical: bool = False):
        self.name = name
        self.url = url
        self.critical = critical
        self.status = ServiceStatus.UNKNOWN
        self.last_check = None
        self.last_success = None
        self.error_count = 0
        self.response_time = None
        self.error_message = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire."""
        return {
            "name": self.name,
            "url": self.url,
            "critical": self.critical,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "error_count": self.error_count,
            "response_time_ms": self.response_time,
            "error_message": self.error_message
        }

class ConnectivityMonitor:
    """
    Moniteur de connectivité pour les services externes.
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialise le moniteur.
        
        Args:
            check_interval: Intervalle entre les vérifications en secondes
        """
        self.check_interval = check_interval
        self.services: Dict[str, ServiceHealth] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.monitoring_active = False
        
        # Services à surveiller
        self._init_services()
    
    def _init_services(self):
        """Initialise la liste des services à surveiller."""
        services_config = [
            # Services Lightning
            ("LNBits", "http://localhost:5001", True),
            ("LNBits Cloud", "https://lnbits.dazno.de", False),
            ("Sparkseer", "https://api.sparkseer.space/v1/", False),
            
            # Bases de données
            ("MongoDB", "mongodb://localhost:27017", True),
            ("Redis", "redis://localhost:6379", True),
            
            # Services API
            ("MCP API", "http://localhost:8000", True),
            ("Lightning API", "http://localhost:8000/api/v1/network/health", False),
            
            # Services externes
            ("OpenAI", "https://api.openai.com", False),
            ("Anthropic", "https://api.anthropic.com", False),
        ]
        
        for name, url, critical in services_config:
            self.services[name] = ServiceHealth(name, url, critical)
    
    async def check_http_service(self, service: ServiceHealth) -> bool:
        """
        Vérifie un service HTTP/HTTPS.
        
        Args:
            service: Service à vérifier
            
        Returns:
            True si le service est disponible
        """
        try:
            import aiohttp
            import time
            
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Pour les services MongoDB et Redis, vérifier différemment
                if "mongodb" in service.url or "redis" in service.url:
                    # Ces services nécessitent des clients spécifiques
                    return await self._check_database_service(service)
                
                async with session.get(service.url) as response:
                    response_time = (time.time() - start_time) * 1000  # en ms
                    
                    if response.status < 500:
                        service.status = ServiceStatus.HEALTHY
                        service.last_success = datetime.now()
                        service.response_time = response_time
                        service.error_count = 0
                        service.error_message = None
                        return True
                    else:
                        service.status = ServiceStatus.DEGRADED
                        service.error_message = f"HTTP {response.status}"
                        return False
                        
        except Exception as e:
            service.status = ServiceStatus.UNAVAILABLE
            service.error_count += 1
            service.error_message = str(e)
            logger.debug(f"Service {service.name} check failed: {str(e)}")
            return False
        finally:
            service.last_check = datetime.now()
    
    async def _check_database_service(self, service: ServiceHealth) -> bool:
        """
        Vérifie un service de base de données.
        
        Args:
            service: Service de base de données à vérifier
            
        Returns:
            True si le service est disponible
        """
        try:
            if "mongodb" in service.url:
                # Test MongoDB
                try:
                    from motor.motor_asyncio import AsyncIOMotorClient
                    client = AsyncIOMotorClient(service.url, serverSelectionTimeoutMS=5000)
                    await client.server_info()
                    service.status = ServiceStatus.HEALTHY
                    service.last_success = datetime.now()
                    service.error_count = 0
                    return True
                except:
                    service.status = ServiceStatus.UNAVAILABLE
                    service.error_count += 1
                    return False
                    
            elif "redis" in service.url:
                # Test Redis
                try:
                    import redis.asyncio as redis
                    client = redis.from_url(service.url)
                    await client.ping()
                    await client.close()
                    service.status = ServiceStatus.HEALTHY
                    service.last_success = datetime.now()
                    service.error_count = 0
                    return True
                except:
                    service.status = ServiceStatus.UNAVAILABLE
                    service.error_count += 1
                    return False
                    
        except ImportError:
            # Si les bibliothèques ne sont pas disponibles, marquer comme inconnu
            service.status = ServiceStatus.UNKNOWN
            service.error_message = "Driver not installed"
            return False
        except Exception as e:
            service.status = ServiceStatus.UNAVAILABLE
            service.error_count += 1
            service.error_message = str(e)
            return False
    
    async def check_all_services(self) -> Dict[str, Any]:
        """
        Vérifie tous les services configurés.
        
        Returns:
            État de tous les services
        """
        logger.info("Vérification de tous les services...")
        
        tasks = []
        for service in self.services.values():
            tasks.append(self.check_http_service(service))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculer les statistiques globales
        healthy_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.HEALTHY)
        degraded_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.DEGRADED)
        unavailable_count = sum(1 for s in self.services.values() if s.status == ServiceStatus.UNAVAILABLE)
        
        # Déterminer l'état global
        critical_unavailable = any(
            s.critical and s.status == ServiceStatus.UNAVAILABLE 
            for s in self.services.values()
        )
        
        overall_status = "critical" if critical_unavailable else \
                        "degraded" if unavailable_count > 0 else \
                        "healthy"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "statistics": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unavailable": unavailable_count,
                "total": len(self.services)
            },
            "services": {
                name: service.to_dict() 
                for name, service in self.services.items()
            }
        }
    
    def generate_alert(self, service: ServiceHealth, alert_type: str, message: str):
        """
        Génère une alerte pour un service.
        
        Args:
            service: Service concerné
            alert_type: Type d'alerte (critical, warning, info)
            message: Message de l'alerte
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "service": service.name,
            "message": message,
            "critical": service.critical
        }
        
        self.alerts.append(alert)
        
        # Garder seulement les 100 dernières alertes
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Logger l'alerte
        if alert_type == "critical":
            logger.error(f"ALERTE CRITIQUE - {service.name}: {message}")
        elif alert_type == "warning":
            logger.warning(f"ALERTE - {service.name}: {message}")
        else:
            logger.info(f"Info - {service.name}: {message}")
    
    async def start_monitoring(self):
        """Démarre la surveillance continue."""
        logger.info("Démarrage de la surveillance de connectivité...")
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                # Vérifier tous les services
                status = await self.check_all_services()
                
                # Générer des alertes si nécessaire
                for service in self.services.values():
                    if service.critical and service.status == ServiceStatus.UNAVAILABLE:
                        if service.error_count == 1:  # Première erreur
                            self.generate_alert(
                                service, 
                                "critical",
                                f"Service critique indisponible: {service.error_message}"
                            )
                        elif service.error_count % 10 == 0:  # Toutes les 10 erreurs
                            self.generate_alert(
                                service,
                                "critical",
                                f"Service toujours indisponible après {service.error_count} tentatives"
                            )
                    
                    # Alerte de récupération
                    if service.error_count == 0 and service.last_success:
                        if service.critical:
                            self.generate_alert(
                                service,
                                "info",
                                "Service récupéré et opérationnel"
                            )
                
                # Afficher le résumé
                logger.info(f"État global: {status['overall_status']} - "
                          f"Services: {status['statistics']['healthy']}/{status['statistics']['total']} healthy")
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Arrête la surveillance."""
        logger.info("Arrêt de la surveillance de connectivité...")
        self.monitoring_active = False
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de l'état actuel.
        
        Returns:
            Résumé de l'état de tous les services
        """
        return {
            "services": {
                name: {
                    "status": service.status.value,
                    "critical": service.critical,
                    "last_check": service.last_check.isoformat() if service.last_check else None,
                    "error_count": service.error_count
                }
                for name, service in self.services.items()
            },
            "recent_alerts": self.alerts[-10:] if self.alerts else []
        }
    
    def get_critical_services_status(self) -> List[Dict[str, Any]]:
        """
        Retourne l'état des services critiques uniquement.
        
        Returns:
            Liste des services critiques avec leur état
        """
        critical_services = []
        for service in self.services.values():
            if service.critical:
                critical_services.append({
                    "name": service.name,
                    "status": service.status.value,
                    "available": service.status == ServiceStatus.HEALTHY,
                    "response_time": service.response_time,
                    "error": service.error_message
                })
        return critical_services


async def main():
    """Point d'entrée pour les tests."""
    monitor = ConnectivityMonitor(check_interval=30)
    
    # Test unique
    logger.info("Test de connectivité unique...")
    status = await monitor.check_all_services()
    
    # Afficher les résultats
    print(json.dumps(status, indent=2))
    
    # Afficher les services critiques
    critical = monitor.get_critical_services_status()
    logger.info(f"Services critiques: {json.dumps(critical, indent=2)}")
    
    # Option pour démarrer la surveillance continue
    # await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())