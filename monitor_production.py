#!/usr/bin/env python3
"""
Monitoring de production MCP - Phase 5

Ce script surveille en temps réel:
1. État de santé de l'API
2. Métriques de performance
3. Logs d'erreurs
4. Actions du Fee Optimizer
5. Système de rollback

Compatible avec déploiement Hostinger et sans Grafana.
Génère des rapports JSON et peut envoyer des alertes Telegram.

Dernière mise à jour: 30 septembre 2025
"""

import asyncio
import httpx
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict

# Configuration
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except ImportError:
    # dotenv not installed, use system env vars
    pass

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / "logs" / "monitoring.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProductionMonitor:
    """Moniteur de production pour MCP"""

    def __init__(self, api_url: str = None, check_interval: int = 60):
        self.api_url = api_url or os.getenv("API_BASE_URL", "https://api.dazno.de")
        self.check_interval = check_interval
        self.metrics = {
            "checks": 0,
            "successes": 0,
            "failures": 0,
            "response_times": [],
            "errors": [],
            "start_time": datetime.now().isoformat()
        }
        self.alert_threshold = 3  # Nombre d'échecs avant alerte
        self.consecutive_failures = 0

        # Configuration Telegram (optionnel)
        self.telegram_enabled = os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        # Cooldown pour éviter le spam d'alertes
        self.last_alert_time = None
        self.alert_cooldown = timedelta(minutes=15)  # 15 minutes entre alertes

        logger.info(f"Monitor initialized - API: {self.api_url}")
        logger.info(f"Check interval: {check_interval}s")
        logger.info(f"Telegram alerts: {'enabled' if self.telegram_enabled else 'disabled'}")

    async def check_health(self) -> Dict[str, Any]:
        """Vérifie l'état de santé de l'API"""
        start = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "healthy": False,
            "response_time": 0,
            "status_code": 0,
            "error": None
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(f"{self.api_url}/health")
                result["status_code"] = response.status_code
                result["response_time"] = (time.time() - start) * 1000  # ms

                if response.status_code == 200:
                    try:
                        data = response.json()
                        result["healthy"] = data.get("status") == "healthy"
                        result["data"] = data
                    except Exception as json_err:
                        result["error"] = f"JSON decode error: {json_err}"
                        logger.error(f"Failed to parse JSON response: {json_err}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Health check failed: {e}")

        return result

    async def check_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de l'API"""
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(f"{self.api_url}/metrics")

                if response.status_code == 200:
                    return response.json()

        except Exception as e:
            logger.error(f"Metrics check failed: {e}")

        return {}

    async def check_optimizer_logs(self) -> Dict[str, Any]:
        """Analyse les logs récents du Fee Optimizer"""
        log_file = ROOT_DIR / "logs" / "fee_optimizer.log"

        if not log_file.exists():
            return {"status": "no_logs", "entries": 0}

        try:
            # Lit les dernières lignes
            with open(log_file, 'r') as f:
                lines = f.readlines()[-100:]  # 100 dernières lignes

            # Analyse
            errors = [l for l in lines if "ERROR" in l or "FAIL" in l]
            warnings = [l for l in lines if "WARN" in l]
            optimizations = [l for l in lines if "optimization" in l.lower()]

            return {
                "status": "ok",
                "total_lines": len(lines),
                "errors": len(errors),
                "warnings": len(warnings),
                "recent_optimizations": len(optimizations),
                "last_error": errors[-1].strip() if errors else None
            }

        except Exception as e:
            logger.error(f"Log analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    async def check_rollback_availability(self) -> Dict[str, Any]:
        """Vérifie la disponibilité du système de rollback"""
        rollback_dir = ROOT_DIR / "data" / "rollbacks"

        try:
            if not rollback_dir.exists():
                return {"status": "missing", "available": False}

            # Compte les backups récents (< 7 jours)
            recent_backups = []
            cutoff = datetime.now() - timedelta(days=7)

            for backup_file in rollback_dir.glob("*.json"):
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if mtime > cutoff:
                    recent_backups.append({
                        "file": backup_file.name,
                        "timestamp": mtime.isoformat()
                    })

            return {
                "status": "ok",
                "available": True,
                "recent_backups": len(recent_backups),
                "backups": recent_backups[-5:]  # 5 derniers
            }

        except Exception as e:
            logger.error(f"Rollback check failed: {e}")
            return {"status": "error", "message": str(e)}

    async def send_telegram_alert(self, message: str):
        """Envoie une alerte via Telegram"""
        if not self.telegram_enabled:
            return

        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": f"🚨 MCP Alert\n\n{message}",
                    "parse_mode": "HTML"
                }
                await client.post(url, json=payload)
                logger.info("Telegram alert sent")

        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    async def perform_check(self):
        """Effectue un cycle complet de vérification"""
        self.metrics["checks"] += 1
        logger.info(f"=== Check #{self.metrics['checks']} ===")

        # 1. Health check
        health = await self.check_health()
        logger.info(f"Health: {'✅' if health['healthy'] else '❌'} ({health['response_time']:.0f}ms)")

        if health["healthy"]:
            self.metrics["successes"] += 1
            self.metrics["response_times"].append(health["response_time"])

            # Service rétabli - envoyer alerte de récupération si on avait des échecs
            if self.consecutive_failures >= self.alert_threshold:
                await self.send_telegram_alert(
                    f"✅ API RÉTABLIE après {self.consecutive_failures} échecs consécutifs"
                )
                self.last_alert_time = None  # Reset cooldown

            self.consecutive_failures = 0
        else:
            self.metrics["failures"] += 1
            self.metrics["errors"].append({
                "timestamp": health["timestamp"],
                "error": health.get("error", "Unknown error")
            })
            self.consecutive_failures += 1

            # Alerte si seuil dépassé ET cooldown respecté
            if self.consecutive_failures == self.alert_threshold:
                # Première alerte au seuil exact
                await self.send_telegram_alert(
                    f"API health check failed {self.consecutive_failures} times\n"
                    f"Last error: {health.get('error', 'Unknown')}"
                )
                self.last_alert_time = datetime.now()
            elif self.consecutive_failures > self.alert_threshold:
                # Alertes suivantes uniquement si cooldown écoulé
                if self.last_alert_time is None or (datetime.now() - self.last_alert_time) > self.alert_cooldown:
                    await self.send_telegram_alert(
                        f"API still down - {self.consecutive_failures} consecutive failures\n"
                        f"Last error: {health.get('error', 'Unknown')}"
                    )
                    self.last_alert_time = datetime.now()

        # 2. Métriques
        metrics = await self.check_metrics()
        if metrics:
            logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")

        # 3. Logs optimizer
        optimizer_logs = await self.check_optimizer_logs()
        if optimizer_logs.get("errors", 0) > 0:
            logger.warning(f"⚠️  Optimizer errors detected: {optimizer_logs['errors']}")

        # 4. Rollback
        rollback = await self.check_rollback_availability()
        logger.info(f"Rollback: {'✅' if rollback['available'] else '❌'} "
                   f"({rollback.get('recent_backups', 0)} recent backups)")

        # Sauvegarde du rapport
        report = {
            "timestamp": datetime.now().isoformat(),
            "check_number": self.metrics["checks"],
            "health": health,
            "metrics": metrics,
            "optimizer_logs": optimizer_logs,
            "rollback": rollback,
            "summary": {
                "uptime_pct": (self.metrics["successes"] / self.metrics["checks"] * 100)
                              if self.metrics["checks"] > 0 else 0,
                "avg_response_time": sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
                                    if self.metrics["response_times"] else 0,
                "consecutive_failures": self.consecutive_failures
            }
        }

        # Sauvegarde du rapport journalier
        report_dir = ROOT_DIR / "monitoring_data"
        report_dir.mkdir(exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        report_file = report_dir / f"monitoring_{today}.json"

        # Charge ou crée le rapport journalier
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    daily_report = json.load(f)
                    # Valide la structure
                    if not isinstance(daily_report, dict) or "checks" not in daily_report:
                        logger.warning(f"Invalid report structure, recreating")
                        daily_report = {"checks": [], "start_date": today}
            except (json.JSONDecodeError, KeyError) as e:
                # Fichier corrompu, on recrée
                logger.warning(f"Corrupted report file ({e}), creating new one")
                daily_report = {"checks": [], "start_date": today}
        else:
            daily_report = {"checks": [], "start_date": today}

        # S'assure que la clé checks existe
        if "checks" not in daily_report:
            daily_report["checks"] = []

        daily_report["checks"].append(report)

        with open(report_file, 'w') as f:
            json.dump(daily_report, f, indent=2)

        logger.info(f"Report saved to {report_file}")

    async def run(self, duration: Optional[int] = None):
        """Lance le monitoring en continu"""
        logger.info("="*60)
        logger.info("🔍 MCP Production Monitor - Phase 5")
        logger.info("="*60)

        start_time = time.time()
        checks = 0

        try:
            while True:
                await self.perform_check()
                checks += 1

                # Vérifie la durée
                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"Duration limit reached ({duration}s)")
                    break

                # Attend avant le prochain check
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Monitoring stopped by user")

        finally:
            # Résumé final
            logger.info("\n" + "="*60)
            logger.info("📊 MONITORING SUMMARY")
            logger.info("="*60)
            logger.info(f"Total checks: {self.metrics['checks']}")
            logger.info(f"Successes: {self.metrics['successes']} ✅")
            logger.info(f"Failures: {self.metrics['failures']} ❌")

            if self.metrics["checks"] > 0:
                uptime = self.metrics["successes"] / self.metrics["checks"] * 100
                logger.info(f"Uptime: {uptime:.1f}%")

            if self.metrics["response_times"]:
                avg_rt = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
                logger.info(f"Avg response time: {avg_rt:.0f}ms")

            logger.info("="*60)


async def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Production Monitor")
    parser.add_argument("--api-url", help="API base URL", default=None)
    parser.add_argument("--interval", type=int, help="Check interval (seconds)", default=60)
    parser.add_argument("--duration", type=int, help="Total duration (seconds)", default=None)

    args = parser.parse_args()

    monitor = ProductionMonitor(api_url=args.api_url, check_interval=args.interval)
    await monitor.run(duration=args.duration)


if __name__ == "__main__":
    asyncio.run(main())
