import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable, Coroutine
from functools import partial

from src.clients.lnbits_client_complete import LNBitsClientComplete
from src.tools.optimize_and_execute import OptimizeAndExecute
from src.tools.metrics_collector import MetricsCollector
from src.tools.backup_manager import BackupManager
from src.tools.monitoring import MonitoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationScheduler:
    """Gestionnaire d'automatisation des tâches MCP."""
    
    def __init__(self, lnbits_client: LNBitsClientComplete):
        self.lnbits_client = lnbits_client
        self.optimizer = OptimizeAndExecute(lnbits_client)
        self.metrics_collector = MetricsCollector()
        self.backup_manager = BackupManager()
        self.monitoring = MonitoringService()
        self.tasks: Dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}
        self.running = False

    async def optimize_fees(self):
        """Optimisation des frais basée sur les métriques."""
        try:
            logger.info("🔄 Début de l'optimisation des frais...")
            channels = await self.lnbits_client.list_channels()
            
            for channel in channels:
                metrics = await self.metrics_collector.get_channel_metrics(channel["channel_id"])
                new_policy = await self.optimizer.calculate_optimal_policy(
                    channel["channel_id"],
                    metrics
                )
                
                if new_policy:
                    await self.lnbits_client.update_channel_policy(
                        channel["channel_id"],
                        new_policy["base_fee"],
                        new_policy["fee_rate"]
                    )
                    
            logger.info("✅ Optimisation des frais terminée")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'optimisation des frais: {str(e)}")
            await self.monitoring.alert("fee_optimization_error", str(e))

    async def collect_metrics(self):
        """Collecte des métriques du réseau."""
        try:
            logger.info("📊 Début de la collecte des métriques...")
            await self.metrics_collector.collect_network_metrics()
            await self.metrics_collector.collect_node_metrics()
            await self.metrics_collector.collect_channel_metrics()
            logger.info("✅ Collecte des métriques terminée")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la collecte des métriques: {str(e)}")
            await self.monitoring.alert("metrics_collection_error", str(e))

    async def perform_backup(self):
        """Exécution des sauvegardes."""
        try:
            logger.info("💾 Début de la sauvegarde...")
            await self.backup_manager.backup_data()
            await self.backup_manager.backup_config()
            await self.backup_manager.cleanup_old_backups()
            logger.info("✅ Sauvegarde terminée")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {str(e)}")
            await self.monitoring.alert("backup_error", str(e))

    async def check_health(self):
        """Vérification de la santé du système."""
        try:
            logger.info("🏥 Vérification de la santé du système...")
            health_status = await self.monitoring.check_system_health()
            
            if not health_status["healthy"]:
                await self.monitoring.alert(
                    "system_health_error",
                    f"Problèmes détectés: {health_status['issues']}"
                )
            
            logger.info("✅ Vérification de la santé terminée")
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification de la santé: {str(e)}")
            await self.monitoring.alert("health_check_error", str(e))

    def schedule_task(self, name: str, task: Callable[[], Coroutine[Any, Any, None]], 
                     interval: int, unit: str = "minutes"):
        """Planifie une tâche récurrente."""
        self.tasks[name] = task
        
        if unit == "minutes":
            schedule.every(interval).minutes.do(
                partial(asyncio.run, task())
            )
        elif unit == "hours":
            schedule.every(interval).hours.do(
                partial(asyncio.run, task())
            )
        elif unit == "days":
            schedule.every(interval).days.do(
                partial(asyncio.run, task())
            )

    async def start(self):
        """Démarre le planificateur de tâches."""
        if self.running:
            return

        self.running = True
        logger.info("🚀 Démarrage du planificateur de tâches...")

        # Planification des tâches récurrentes
        self.schedule_task("optimize_fees", self.optimize_fees, 15)  # Toutes les 15 minutes
        self.schedule_task("collect_metrics", self.collect_metrics, 5)  # Toutes les 5 minutes
        self.schedule_task("perform_backup", self.perform_backup, 24, "hours")  # Toutes les 24 heures
        self.schedule_task("check_health", self.check_health, 10)  # Toutes les 10 minutes

        while self.running:
            try:
                schedule.run_pending()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {str(e)}")
                await self.monitoring.alert("scheduler_error", str(e))

    async def stop(self):
        """Arrête le planificateur de tâches."""
        self.running = False
        logger.info("🛑 Arrêt du planificateur de tâches...")
        schedule.clear()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop() 