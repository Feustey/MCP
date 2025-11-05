"""
Scheduler pour les rapports quotidiens
Gestion automatisée des tâches planifiées avec APScheduler

Auteur: MCP Team
Version: 1.0.0
Dernière mise à jour: 5 novembre 2025
"""

import logging
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger(__name__)


class DailyReportScheduler:
    """Scheduler pour les rapports quotidiens"""
    
    def __init__(self, report_generator):
        """
        Initialise le scheduler
        
        Args:
            report_generator: Instance de DailyReportGenerator
        """
        self.report_generator = report_generator
        self.logger = logging.getLogger(__name__)
        
        # Configuration du scheduler
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,  # Combine les exécutions manquées
            'max_instances': 1,  # Une seule instance à la fois
            'misfire_grace_time': 3600  # 1 heure de tolérance
        }
        
        self.scheduler = AsyncIOScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Configuration depuis l'environnement
        self.schedule_hour = int(os.getenv("DAILY_REPORTS_HOUR", "6"))
        self.schedule_minute = int(os.getenv("DAILY_REPORTS_MINUTE", "0"))
        self.enabled = os.getenv("DAILY_REPORTS_SCHEDULER_ENABLED", "true").lower() == "true"
    
    def start(self):
        """Démarre le scheduler"""
        
        if not self.enabled:
            self.logger.warning("Daily report scheduler is disabled via configuration")
            return
        
        try:
            # Job quotidien à l'heure configurée (défaut: 06:00 UTC)
            self.scheduler.add_job(
                self._run_daily_reports,
                trigger=CronTrigger(
                    hour=self.schedule_hour,
                    minute=self.schedule_minute,
                    timezone='UTC'
                ),
                id="daily_reports_generation",
                name="Génération rapports quotidiens",
                replace_existing=True
            )
            
            self.scheduler.start()
            
            self.logger.info(
                f"Daily report scheduler started - will run daily at "
                f"{self.schedule_hour:02d}:{self.schedule_minute:02d} UTC"
            )
            
        except Exception as e:
            self.logger.error(f"Error starting daily report scheduler: {e}")
            raise
    
    def stop(self):
        """Arrête le scheduler"""
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self.logger.info("Daily report scheduler stopped")
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")
    
    async def _run_daily_reports(self):
        """Exécute la génération des rapports quotidiens"""
        
        start_time = datetime.utcnow()
        self.logger.info("=" * 80)
        self.logger.info("Starting scheduled daily reports generation")
        self.logger.info("=" * 80)
        
        try:
            await self.report_generator.run()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(
                f"Scheduled daily reports generation completed successfully "
                f"in {duration:.2f}s"
            )
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(
                f"Error in scheduled daily reports generation after {duration:.2f}s: {e}",
                exc_info=True
            )
        finally:
            self.logger.info("=" * 80)
    
    def get_next_run_time(self) -> str:
        """Retourne la prochaine exécution planifiée"""
        
        try:
            job = self.scheduler.get_job("daily_reports_generation")
            if job:
                next_run = job.next_run_time
                return next_run.isoformat() if next_run else "Not scheduled"
            return "Not scheduled"
        except Exception:
            return "Unknown"
    
    def get_status(self) -> dict:
        """Retourne le statut du scheduler"""
        
        return {
            "enabled": self.enabled,
            "running": self.scheduler.running if hasattr(self.scheduler, 'running') else False,
            "schedule": f"{self.schedule_hour:02d}:{self.schedule_minute:02d} UTC",
            "next_run": self.get_next_run_time(),
            "job_count": len(self.scheduler.get_jobs())
        }


# Instance globale du scheduler
_scheduler_instance = None

def get_scheduler(report_generator) -> DailyReportScheduler:
    """Récupère ou crée l'instance du scheduler"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = DailyReportScheduler(report_generator)
    
    return _scheduler_instance

