"""
Système d'alertes Telegram pour monitoring des services MCP
Surveille la disponibilité des services et envoie des notifications
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("mcp.telegram_alerts")

class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "🟢"
    WARNING = "🟡" 
    ERROR = "🔴"
    CRITICAL = "🚨"

class ServiceStatus(Enum):
    """Statuts des services"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class Service:
    """Configuration d'un service à monitorer"""
    name: str
    url: str
    method: str = "GET"
    timeout: int = 10
    expected_status: int = 200
    headers: Dict[str, str] = None
    check_interval: int = 60  # secondes
    alert_after_failures: int = 3  # alerter après N échecs consécutifs

@dataclass
class Alert:
    """Alerte à envoyer"""
    service_name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

class TelegramAlerter:
    """
    Gestionnaire d'alertes Telegram pour surveillance des services
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # État des services
        self.service_statuses: Dict[str, ServiceStatus] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_alerts: Dict[str, datetime] = {}
        
        # Configuration
        self.alert_cooldown = timedelta(minutes=15)  # Éviter le spam
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
    
    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Envoie un message Telegram"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Message Telegram envoyé avec succès")
                    return True
                else:
                    logger.error(f"Erreur envoi Telegram: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erreur envoi message Telegram: {str(e)}")
            return False
    
    async def check_service(self, service: Service) -> ServiceStatus:
        """Vérifie le statut d'un service"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            headers = service.headers or {}
            timeout = aiohttp.ClientTimeout(total=service.timeout)
            
            async with self.session.request(
                service.method, 
                service.url, 
                headers=headers,
                timeout=timeout
            ) as response:
                
                if response.status == service.expected_status:
                    return ServiceStatus.UP
                elif 500 <= response.status < 600:
                    return ServiceStatus.DOWN
                else:
                    return ServiceStatus.DEGRADED
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout pour {service.name}")
            return ServiceStatus.DOWN
        except aiohttp.ClientError as e:
            logger.warning(f"Erreur client pour {service.name}: {str(e)}")
            return ServiceStatus.DOWN
        except Exception as e:
            logger.error(f"Erreur inattendue pour {service.name}: {str(e)}")
            return ServiceStatus.UNKNOWN
    
    async def process_service_status(self, service: Service, status: ServiceStatus) -> Optional[Alert]:
        """Traite le statut d'un service et génère une alerte si nécessaire"""
        previous_status = self.service_statuses.get(service.name)
        self.service_statuses[service.name] = status
        
        # Gérer les compteurs d'échecs
        if status == ServiceStatus.UP:
            if service.name in self.failure_counts:
                # Service rétabli
                if self.failure_counts[service.name] >= service.alert_after_failures:
                    alert = Alert(
                        service_name=service.name,
                        level=AlertLevel.INFO,
                        message=f"✅ Service {service.name} RÉTABLI",
                        timestamp=datetime.utcnow(),
                        details={"previous_failures": self.failure_counts[service.name]}
                    )
                    self.failure_counts[service.name] = 0
                    return alert
                else:
                    self.failure_counts[service.name] = 0
        else:
            # Service en échec
            self.failure_counts[service.name] = self.failure_counts.get(service.name, 0) + 1
            
            # Alerter après N échecs consécutifs
            if self.failure_counts[service.name] == service.alert_after_failures:
                level = AlertLevel.ERROR if status == ServiceStatus.DOWN else AlertLevel.WARNING
                
                alert = Alert(
                    service_name=service.name,
                    level=level,
                    message=f"{level.value} Service {service.name} INDISPONIBLE",
                    timestamp=datetime.utcnow(),
                    details={
                        "status": status.value,
                        "consecutive_failures": self.failure_counts[service.name],
                        "url": service.url
                    }
                )
                return alert
        
        return None
    
    async def should_send_alert(self, alert: Alert) -> bool:
        """Détermine si l'alerte doit être envoyée (cooldown)"""
        last_alert_time = self.last_alerts.get(alert.service_name)
        
        if last_alert_time is None:
            return True
            
        if datetime.utcnow() - last_alert_time > self.alert_cooldown:
            return True
            
        # Toujours envoyer les alertes critiques et de rétablissement
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.INFO]:
            return True
            
        return False
    
    async def send_alert(self, alert: Alert) -> bool:
        """Envoie une alerte Telegram"""
        if not await self.should_send_alert(alert):
            logger.debug(f"Alerte ignorée (cooldown): {alert.service_name}")
            return False
            
        # Formater le message
        message = self._format_alert_message(alert)
        
        # Envoyer
        success = await self.send_message(message)
        
        if success:
            self.last_alerts[alert.service_name] = alert.timestamp
            
        return success
    
    def _format_alert_message(self, alert: Alert) -> str:
        """Formate un message d'alerte"""
        timestamp = alert.timestamp.strftime("%H:%M:%S")
        
        message = f"""
{alert.level.value} *ALERTE MCP LIGHTNING*

🔧 **Service**: {alert.service_name}
⏰ **Heure**: {timestamp}
📝 **Message**: {alert.message}
"""
        
        if alert.details:
            message += "\n📊 **Détails**:\n"
            for key, value in alert.details.items():
                message += f"• {key}: `{value}`\n"
        
        message += f"\n🌐 **Environnement**: Production"
        message += f"\n📱 **Système**: MCP Lightning Network API"
        
        return message.strip()

class ServiceMonitor:
    """
    Moniteur de services avec alertes Telegram
    """
    
    def __init__(self, telegram_bot_token: str, telegram_chat_id: str):
        self.alerter = TelegramAlerter(telegram_bot_token, telegram_chat_id)
        self.services: List[Service] = []
        self.monitoring = False
        
    def add_service(self, service: Service):
        """Ajoute un service à monitorer"""
        self.services.append(service)
        logger.info(f"Service ajouté au monitoring: {service.name}")
    
    def add_mcp_services(self):
        """Ajoute les services MCP standards"""
        # API principale
        self.add_service(Service(
            name="MCP API",
            url="https://api.dazno.de/health",
            headers={"Authorization": "Bearer mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4"},
            check_interval=60,
            alert_after_failures=2
        ))
        
        # LNBits
        self.add_service(Service(
            name="LNBits",
            url="https://api.dazno.de:5001/api/v1/wallet",
            check_interval=120,
            alert_after_failures=3
        ))
        
        # Documentation
        self.add_service(Service(
            name="API Documentation",
            url="https://api.dazno.de/docs",
            check_interval=300,
            alert_after_failures=5
        ))
        
        # Nginx
        self.add_service(Service(
            name="Reverse Proxy",
            url="https://api.dazno.de/",
            check_interval=180,
            alert_after_failures=2
        ))
    
    async def start_monitoring(self):
        """Démarre le monitoring en continu"""
        self.monitoring = True
        logger.info("Démarrage du monitoring des services")
        
        async with self.alerter:
            # Message de démarrage
            await self.alerter.send_message(
                "🚀 *MCP Service Monitor DÉMARRÉ*\n\n"
                f"📊 Services surveillés: {len(self.services)}\n"
                f"🕐 Monitoring actif 24/7"
            )
            
            # Boucle de monitoring
            while self.monitoring:
                tasks = []
                
                for service in self.services:
                    task = asyncio.create_task(self._monitor_service(service))
                    tasks.append(task)
                
                # Attendre que tous les checks soient terminés
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Pause avant le prochain cycle
                await asyncio.sleep(min(s.check_interval for s in self.services))
    
    async def _monitor_service(self, service: Service):
        """Monitore un service spécifique"""
        try:
            status = await self.alerter.check_service(service)
            alert = await self.alerter.process_service_status(service, status)
            
            if alert:
                await self.alerter.send_alert(alert)
                
        except Exception as e:
            logger.error(f"Erreur monitoring {service.name}: {str(e)}")
    
    async def stop_monitoring(self):
        """Arrête le monitoring"""
        self.monitoring = False
        logger.info("Arrêt du monitoring des services")
        
        async with self.alerter:
            await self.alerter.send_message(
                "🛑 *MCP Service Monitor ARRÊTÉ*\n\n"
                "Le monitoring des services a été interrompu."
            )
    
    async def send_status_report(self):
        """Envoie un rapport de statut"""
        async with self.alerter:
            report = "📊 *RAPPORT DE STATUT MCP*\n\n"
            
            for service_name, status in self.alerter.service_statuses.items():
                status_icon = {
                    ServiceStatus.UP: "✅",
                    ServiceStatus.DOWN: "❌", 
                    ServiceStatus.DEGRADED: "⚠️",
                    ServiceStatus.UNKNOWN: "❓"
                }.get(status, "❓")
                
                failures = self.alerter.failure_counts.get(service_name, 0)
                report += f"{status_icon} **{service_name}**: {status.value}"
                
                if failures > 0:
                    report += f" ({failures} échecs)"
                    
                report += "\n"
            
            report += f"\n🕐 **Dernière vérification**: {datetime.utcnow().strftime('%H:%M:%S')}"
            
            await self.alerter.send_message(report)

# ============================================================================
# SCRIPT PRINCIPAL DE MONITORING
# ============================================================================

async def main():
    """Point d'entrée principal du monitoring"""
    # Configuration depuis variables d'environnement
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("Variables TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID requises")
        return
    
    # Créer le moniteur
    monitor = ServiceMonitor(bot_token, chat_id)
    monitor.add_mcp_services()
    
    try:
        # Démarrer le monitoring
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale du monitoring: {str(e)}")
    finally:
        await monitor.stop_monitoring()

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Lancer le monitoring
    asyncio.run(main())