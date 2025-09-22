#!/usr/bin/env python3
"""
Système de surveillance de production pour MCP.
Active la surveillance continue avec alertes et reporting.
"""

import asyncio
import logging
import json
import os
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configuration du logging
def setup_logging():
    """Configure le logging pour la production."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "structured")
    
    if log_format == "structured":
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='{"timestamp":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(
                    os.getenv("LOG_FILE_PATH", "logs/mcp_monitoring.log")
                ) if os.getenv("LOG_FILE_ENABLED", "true") == "true" else None
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

setup_logging()
logger = logging.getLogger(__name__)

class ProductionMonitor:
    """
    Système de surveillance de production complet.
    """
    
    def __init__(self):
        self.monitoring_active = False
        self.check_interval = int(os.getenv("CONNECTIVITY_CHECK_INTERVAL", "60"))
        self.alert_level = os.getenv("ALERT_LEVEL", "warning")
        
        # Services critiques
        self.critical_services = os.getenv("CRITICAL_SERVICES", "LNBits,MongoDB,Redis,MCP_API").split(",")
        
        # Services à surveiller
        monitor_services = os.getenv("MONITOR_SERVICES", "").split(",") if os.getenv("MONITOR_SERVICES") else []
        
        # Statistiques
        self.stats = {
            "uptime_start": datetime.now(),
            "checks_performed": 0,
            "alerts_sent": 0,
            "last_check": None,
            "services_status": {}
        }
        
        # Historique des alertes
        self.alert_history = []
        
        # Notifications
        self.telegram_enabled = os.getenv("TELEGRAM_NOTIFICATIONS_ENABLED", "false") == "true"
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Initialiser le moniteur de connectivité
        self._init_connectivity_monitor()
    
    def _init_connectivity_monitor(self):
        """Initialise le moniteur de connectivité."""
        try:
            from src.monitoring.connectivity_monitor import ConnectivityMonitor
            self.connectivity_monitor = ConnectivityMonitor(check_interval=self.check_interval)
            logger.info("Moniteur de connectivité initialisé")
        except ImportError:
            logger.warning("Module de connectivité non disponible, utilisation du mode simplifié")
            self.connectivity_monitor = None
    
    async def send_telegram_alert(self, message: str, level: str = "info"):
        """Envoie une alerte via Telegram."""
        if not self.telegram_enabled or not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            import httpx
            
            # Formatage du message
            emoji_map = {
                "critical": "🚨",
                "warning": "⚠️",
                "info": "ℹ️",
                "success": "✅"
            }
            
            emoji = emoji_map.get(level, "📊")
            formatted_message = f"{emoji} MCP Monitoring\\n\\n{message}\\n\\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=10)
                if response.status_code == 200:
                    logger.debug("Alerte Telegram envoyée")
                    self.stats["alerts_sent"] += 1
                else:
                    logger.warning(f"Erreur Telegram: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {str(e)}")
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Vérifie l'état global du système."""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "services": {},
            "system": {},
            "alerts": []
        }
        
        try:
            # Vérification des services via le moniteur de connectivité
            if self.connectivity_monitor:
                connectivity_status = await self.connectivity_monitor.check_all_services()
                health_data["services"] = connectivity_status.get("services", {})
                health_data["overall_status"] = connectivity_status.get("overall_status", "unknown")
                
                # Mettre à jour les statistiques des services
                for service_name, service_data in health_data["services"].items():
                    self.stats["services_status"][service_name] = {
                        "status": service_data.get("status", "unknown"),
                        "last_check": datetime.now().isoformat()
                    }
            else:
                # Mode simplifié sans moniteur de connectivité
                health_data["overall_status"] = "limited"
                health_data["services"] = {"monitoring": {"status": "limited", "message": "Monitoring simplifié actif"}}
            
            # Informations système
            try:
                import psutil
                health_data["system"] = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent
                }
            except ImportError:
                health_data["system"] = {"message": "psutil non disponible"}
            
            # Uptime
            uptime = datetime.now() - self.stats["uptime_start"]
            health_data["uptime_seconds"] = uptime.total_seconds()
            
            self.stats["checks_performed"] += 1
            self.stats["last_check"] = datetime.now().isoformat()
            
            return health_data
            
        except Exception as e:
            logger.error(f"Erreur vérification santé système: {str(e)}")
            health_data["overall_status"] = "error"
            health_data["error"] = str(e)
            return health_data
    
    async def process_health_alerts(self, health_data: Dict[str, Any]):
        """Traite les alertes basées sur l'état de santé."""
        current_time = datetime.now()
        
        # Alerte pour l'état global
        overall_status = health_data.get("overall_status", "unknown")
        
        if overall_status == "critical":
            alert_message = "🚨 *ALERTE CRITIQUE*\\n\\nLe système MCP présente des problèmes critiques.\\n\\n"
            
            # Détailler les services en erreur
            critical_services_down = []
            for service_name, service_data in health_data.get("services", {}).items():
                if service_name in self.critical_services and service_data.get("status") == "unavailable":
                    critical_services_down.append(service_name)
            
            if critical_services_down:
                alert_message += f"Services critiques indisponibles: {', '.join(critical_services_down)}"
            
            await self.send_telegram_alert(alert_message, "critical")
            self.alert_history.append({
                "timestamp": current_time.isoformat(),
                "level": "critical",
                "message": alert_message
            })
        
        elif overall_status == "degraded" and self.alert_level in ["warning", "info"]:
            services_with_issues = []
            for service_name, service_data in health_data.get("services", {}).items():
                if service_data.get("status") in ["unavailable", "degraded"]:
                    services_with_issues.append(service_name)
            
            if services_with_issues:
                alert_message = f"⚠️ *Services dégradés*\\n\\n{', '.join(services_with_issues)}"
                await self.send_telegram_alert(alert_message, "warning")
                self.alert_history.append({
                    "timestamp": current_time.isoformat(),
                    "level": "warning",
                    "message": alert_message
                })
        
        # Alerte pour les ressources système
        system_data = health_data.get("system", {})
        if "cpu_percent" in system_data:
            cpu_percent = system_data["cpu_percent"]
            memory_percent = system_data["memory_percent"]
            
            if cpu_percent > 90 or memory_percent > 90:
                alert_message = f"🔥 *Ressources élevées*\\n\\nCPU: {cpu_percent:.1f}%\\nMémoire: {memory_percent:.1f}%"
                await self.send_telegram_alert(alert_message, "warning")
        
        # Nettoyer l'historique des alertes (garder 100 dernières)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    async def generate_daily_report(self):
        """Génère un rapport quotidien."""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        report = f"""
📊 *Rapport quotidien MCP*

⏱️ *Uptime*: {uptime.days}j {uptime.seconds//3600}h
🔍 *Vérifications*: {self.stats['checks_performed']}
🚨 *Alertes envoyées*: {self.stats['alerts_sent']}

📈 *Services surveillés*: {len(self.stats['services_status'])}
"""
        
        # État des services
        healthy_services = sum(1 for s in self.stats['services_status'].values() if s['status'] == 'healthy')
        total_services = len(self.stats['services_status'])
        
        if total_services > 0:
            report += f"✅ *Services opérationnels*: {healthy_services}/{total_services}\n"
        
        await self.send_telegram_alert(report, "info")
    
    def _serialize_for_json(self, obj):
        """Convertit les objets non-sérialisables en JSON."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        else:
            return obj

    async def save_monitoring_data(self):
        """Sauvegarde les données de monitoring."""
        try:
            # Convertir récursivement tous les objets datetime
            serializable_stats = self._serialize_for_json(self.stats)
            serializable_alert_history = self._serialize_for_json(self.alert_history[-20:])
            
            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "stats": serializable_stats,
                "alert_history": serializable_alert_history,
                "config": {
                    "check_interval": self.check_interval,
                    "alert_level": self.alert_level,
                    "critical_services": self.critical_services
                }
            }
            
            # Créer le répertoire de monitoring
            os.makedirs("monitoring_data", exist_ok=True)
            
            # Sauvegarder
            filename = f"monitoring_data/monitoring_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, "w") as f:
                json.dump(monitoring_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données de monitoring: {str(e)}")
            # Fallback vers logging simple en cas d'erreur persistante
            logger.info(f"Stats actuelles: checks={self.stats.get('checks_performed', 0)}, alerts={self.stats.get('alerts_sent', 0)}")
    
    async def start_monitoring(self):
        """Démarre la surveillance continue."""
        logger.info(f"🚀 Démarrage de la surveillance de production MCP")
        logger.info(f"Intervalle de vérification: {self.check_interval}s")
        logger.info(f"Services critiques: {', '.join(self.critical_services)}")
        logger.info(f"Alertes Telegram: {'activées' if self.telegram_enabled else 'désactivées'}")
        
        self.monitoring_active = True
        
        # Envoyer une alerte de démarrage
        await self.send_telegram_alert(
            f"🟢 *Surveillance MCP démarrée*\\n\\nIntervalle: {self.check_interval}s\\nServices critiques: {len(self.critical_services)}", 
            "info"
        )
        
        last_daily_report = datetime.now().date()
        
        while self.monitoring_active:
            try:
                # Vérification de santé
                health_data = await self.check_system_health()
                
                # Traitement des alertes
                await self.process_health_alerts(health_data)
                
                # Sauvegarde périodique (toutes les heures)
                if self.stats["checks_performed"] % 60 == 0:
                    await self.save_monitoring_data()
                    logger.info(f"Données de monitoring sauvegardées ({self.stats['checks_performed']} vérifications)")
                
                # Rapport quotidien
                current_date = datetime.now().date()
                if current_date > last_daily_report:
                    await self.generate_daily_report()
                    last_daily_report = current_date
                
                # Log de status périodique
                if self.stats["checks_performed"] % 10 == 0:
                    logger.info(f"Monitoring actif - Status global: {health_data.get('overall_status', 'unknown')}")
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Arrête la surveillance."""
        logger.info("Arrêt de la surveillance de production...")
        self.monitoring_active = False
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Retourne un résumé du statut actuel."""
        uptime = datetime.now() - self.stats["uptime_start"]
        
        return {
            "monitoring_active": self.monitoring_active,
            "uptime_seconds": uptime.total_seconds(),
            "checks_performed": self.stats["checks_performed"],
            "alerts_sent": self.stats["alerts_sent"],
            "last_check": self.stats["last_check"],
            "services_count": len(self.stats["services_status"]),
            "recent_alerts": self.alert_history[-5:] if self.alert_history else []
        }

# Instance globale du moniteur
monitor = ProductionMonitor()

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre."""
    logger.info(f"Signal {signum} reçu, arrêt du monitoring...")
    monitor.stop_monitoring()

async def main():
    """Point d'entrée principal pour le monitoring de production."""
    # Configuration des signaux
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Démarrer la surveillance
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée")
    except Exception as e:
        logger.error(f"Erreur dans le monitoring principal: {str(e)}")
        await monitor.send_telegram_alert(f"🚨 *Erreur critique monitoring*\\n\\n{str(e)}", "critical")
    finally:
        # Notification d'arrêt
        await monitor.send_telegram_alert("🔴 *Surveillance MCP arrêtée*", "warning")
        
        # Sauvegarde finale
        await monitor.save_monitoring_data()
        
        logger.info("Monitoring de production arrêté")

if __name__ == "__main__":
    # Vérifier que nous sommes en mode production
    if os.getenv("DEVELOPMENT_MODE", "false") == "true":
        logger.warning("⚠️  Mode développement détecté - Le monitoring de production ne devrait pas être utilisé en développement")
        print("Utiliser 'python test_lightweight_system.py' pour les tests de développement")
        exit(1)
    
    asyncio.run(main())