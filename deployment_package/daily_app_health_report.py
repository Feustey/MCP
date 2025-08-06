#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de rapport quotidien de santé de l'application MCP
Surveille les KPI de santé de l'app et l'utilisation des endpoints sur 24h

Usage:
    python scripts/daily_app_health_report.py
"""

import os
import sys
import json
import asyncio
import logging
import requests
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
import psutil

# Ajouter le répertoire parent au chemin Python
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

class AppHealthReporter:
    """Générateur de rapport quotidien de santé de l'application MCP"""
    
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.endpoints_to_monitor = [
            # Endpoints critiques
            "/health",
            "/health/detailed",
            "/metrics",
            "/metrics/detailed",
            
            # Intelligence et analyse
            "/intelligence/health",
            "/intelligence/metrics", 
            
            # Optimisation des frais
            "/fee-optimizer/status",
            "/fee-optimizer/recommendations",
            
            # Nœuds et canaux
            "/nodes",
            "/lightning/network/global-stats",
            
            # Analytics
            "/analytics/dazflow/network-health",
            
            # Admin
            "/admin/status",
        ]
        
    def send_telegram_message(self, message: str) -> bool:
        """Envoie un message formaté sur Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Configuration Telegram manquante")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data)
            if response.status_code == 200:
                logger.info("Rapport de santé envoyé avec succès sur Telegram")
                return True
            else:
                logger.error(f"Erreur Telegram: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Exception lors de l'envoi Telegram: {str(e)}")
            return False

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques système"""
        try:
            system_metrics = {
                "timestamp": datetime.now(),
                "uptime_seconds": 0,
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "load_average": [0.0, 0.0, 0.0],
                "network_io": {"bytes_sent": 0, "bytes_recv": 0}
            }
            
            # CPU
            system_metrics["cpu_usage"] = psutil.cpu_percent(interval=1)
            
            # Mémoire
            memory = psutil.virtual_memory()
            system_metrics["memory_usage"] = memory.percent
            system_metrics["memory_total_gb"] = round(memory.total / 1024**3, 2)
            system_metrics["memory_available_gb"] = round(memory.available / 1024**3, 2)
            
            # Disque
            disk = psutil.disk_usage('/')
            system_metrics["disk_usage"] = round((disk.used / disk.total) * 100, 2)
            system_metrics["disk_total_gb"] = round(disk.total / 1024**3, 2)
            system_metrics["disk_free_gb"] = round(disk.free / 1024**3, 2)
            
            # Load average (si disponible)
            if hasattr(psutil, 'getloadavg'):
                system_metrics["load_average"] = list(psutil.getloadavg())
            
            # Network IO
            network = psutil.net_io_counters()
            system_metrics["network_io"] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
            # Uptime du système
            system_metrics["uptime_seconds"] = int(psutil.boot_time())
            
            return system_metrics
            
        except Exception as e:
            logger.error(f"Erreur collecte métriques système: {str(e)}")
            return {
                "timestamp": datetime.now(),
                "error": str(e),
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0
            }

    async def test_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Test un endpoint et mesure ses performances"""
        url = f"{self.api_base_url}{endpoint}"
        result = {
            "endpoint": endpoint,
            "url": url,
            "status": "unknown",
            "response_time_ms": 0,
            "status_code": 0,
            "error": None,
            "response_size": 0
        }
        
        try:
            start_time = datetime.now()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result.update({
                "status": "success" if response.status_code < 400 else "error",
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "response_size": len(response.content) if response.content else 0
            })
            
            # Vérifier le contenu si c'est du JSON
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    json_data = response.json()
                    result["response_data"] = json_data
            except:
                pass
                
        except httpx.TimeoutException:
            result.update({
                "status": "timeout",
                "error": "Timeout après 10 secondes"
            })
        except httpx.ConnectError:
            result.update({
                "status": "connection_error",
                "error": "Impossible de se connecter à l'API"
            })
        except Exception as e:
            result.update({
                "status": "error",
                "error": str(e)
            })
            
        return result

    async def get_api_health_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques de santé de l'API"""
        try:
            # Test de l'endpoint de santé détaillé
            health_result = await self.test_endpoint("/health/detailed")
            metrics_result = await self.test_endpoint("/metrics/detailed")
            
            api_metrics = {
                "timestamp": datetime.now(),
                "api_status": "unknown",
                "health_check": health_result,
                "metrics_check": metrics_result,
                "components_status": {},
                "performance": {}
            }
            
            # Analyser les résultats de santé
            if health_result["status"] == "success" and "response_data" in health_result:
                health_data = health_result["response_data"]
                api_metrics["api_status"] = health_data.get("overall", "unknown")
                api_metrics["components_status"] = health_data.get("components", {})
                
            # Analyser les métriques
            if metrics_result["status"] == "success" and "response_data" in metrics_result:
                metrics_data = metrics_result["response_data"]
                api_metrics["performance"] = {
                    "response_time_health": health_result["response_time_ms"],
                    "response_time_metrics": metrics_result["response_time_ms"]
                }
                
                # Extraire les métriques système de l'API si disponibles
                if "system_metrics" in metrics_data:
                    api_metrics["api_system_metrics"] = metrics_data["system_metrics"]
                    
            return api_metrics
            
        except Exception as e:
            logger.error(f"Erreur collecte métriques API: {str(e)}")
            return {
                "timestamp": datetime.now(),
                "error": str(e),
                "api_status": "error"
            }

    async def test_all_endpoints(self) -> Dict[str, Any]:
        """Test tous les endpoints surveillés"""
        logger.info(f"Test de {len(self.endpoints_to_monitor)} endpoints...")
        
        endpoint_results = []
        successful_endpoints = 0
        total_response_time = 0
        
        # Tester tous les endpoints en parallèle
        tasks = [self.test_endpoint(endpoint) for endpoint in self.endpoints_to_monitor]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                endpoint_results.append({
                    "endpoint": self.endpoints_to_monitor[i],
                    "status": "error",
                    "error": str(result)
                })
            else:
                endpoint_results.append(result)
                if result["status"] == "success":
                    successful_endpoints += 1
                    total_response_time += result["response_time_ms"]
        
        # Calculer les statistiques
        success_rate = (successful_endpoints / len(self.endpoints_to_monitor)) * 100
        avg_response_time = total_response_time / successful_endpoints if successful_endpoints > 0 else 0
        
        # Identifier les endpoints lents (>2000ms) et en erreur
        slow_endpoints = [r for r in endpoint_results if r.get("response_time_ms", 0) > 2000]
        error_endpoints = [r for r in endpoint_results if r["status"] != "success"]
        
        return {
            "timestamp": datetime.now(),
            "total_endpoints": len(self.endpoints_to_monitor),
            "successful_endpoints": successful_endpoints,
            "success_rate": round(success_rate, 2),
            "average_response_time": round(avg_response_time, 2),
            "slow_endpoints": slow_endpoints,
            "error_endpoints": error_endpoints,
            "all_results": endpoint_results
        }

    def format_bytes(self, bytes_value: int) -> str:
        """Formate les octets en unité lisible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def get_status_emoji(self, status: str, value: float = None, threshold: float = None) -> str:
        """Retourne l'émoji approprié selon le statut"""
        if status == "healthy" or status == "success":
            return "🟢"
        elif status == "degraded" or status == "warning":
            return "🟡"
        elif status == "unhealthy" or status == "error":
            return "🔴"
        elif status == "timeout":
            return "⏰"
        elif status == "connection_error":
            return "🔌"
        
        # Pour les valeurs numériques avec seuils
        if value is not None and threshold is not None:
            if value < threshold * 0.7:
                return "🟢"
            elif value < threshold:
                return "🟡"
            else:
                return "🔴"
                
        return "⚪"

    def format_health_report(self, system_metrics: Dict, api_metrics: Dict, endpoints_test: Dict) -> str:
        """Formate le rapport de santé pour Telegram"""
        
        # Déterminer le statut global
        api_status = api_metrics.get("api_status", "unknown")
        endpoints_success_rate = endpoints_test.get("success_rate", 0)
        cpu_usage = system_metrics.get("cpu_usage", 0)
        memory_usage = system_metrics.get("memory_usage", 0)
        disk_usage = system_metrics.get("disk_usage", 0)
        
        # Statut global basé sur plusieurs critères
        if (api_status == "healthy" and endpoints_success_rate >= 90 and 
            cpu_usage < 80 and memory_usage < 85 and disk_usage < 90):
            global_status = "🟢 EXCELLENT"
        elif (api_status in ["healthy", "degraded"] and endpoints_success_rate >= 75 and 
              cpu_usage < 90 and memory_usage < 90 and disk_usage < 95):
            global_status = "🟡 ACCEPTABLE"
        else:
            global_status = "🔴 ATTENTION"

        report = f"""🏥 <b>RAPPORT SANTÉ APPLICATION MCP</b> {global_status.split()[0]}
📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}

<b>📊 STATUT GLOBAL</b>
┣━ Application: <b>{global_status}</b>
┣━ API Status: <b>{api_status.upper()}</b> {self.get_status_emoji(api_status)}
┗━ Endpoints: <b>{endpoints_test['success_rate']:.1f}%</b> ({endpoints_test['successful_endpoints']}/{endpoints_test['total_endpoints']})

<b>🖥️ RESSOURCES SYSTÈME</b>
┣━ CPU: <b>{cpu_usage:.1f}%</b> {self.get_status_emoji('', cpu_usage, 80)}
┣━ Mémoire: <b>{memory_usage:.1f}%</b> ({system_metrics.get('memory_available_gb', 0):.1f}GB libre) {self.get_status_emoji('', memory_usage, 85)}
┣━ Disque: <b>{disk_usage:.1f}%</b> ({system_metrics.get('disk_free_gb', 0):.1f}GB libre) {self.get_status_emoji('', disk_usage, 90)}
┗━ Load: <b>{system_metrics.get('load_average', [0,0,0])[0]:.2f}</b>

<b>⚡ PERFORMANCE API</b>
┣━ Temps moyen: <b>{endpoints_test['average_response_time']:.0f}ms</b>
┣━ Santé endpoint: <b>{api_metrics['health_check']['response_time_ms']:.0f}ms</b> {self.get_status_emoji(api_metrics['health_check']['status'])}
┗━ Métriques endpoint: <b>{api_metrics['metrics_check']['response_time_ms']:.0f}ms</b> {self.get_status_emoji(api_metrics['metrics_check']['status'])}"""

        # Ajouter l'état des composants
        if api_metrics.get("components_status"):
            report += "\n\n<b>🔧 COMPOSANTS</b>"
            for component, status in api_metrics["components_status"].items():
                if isinstance(status, dict):
                    comp_status = status.get("status", "unknown")
                    emoji = self.get_status_emoji(comp_status)
                    report += f"\n┣━ {component.upper()}: <b>{comp_status.upper()}</b> {emoji}"

        # Ajouter les endpoints en erreur si il y en a
        if endpoints_test["error_endpoints"]:
            report += "\n\n<b>❌ ENDPOINTS EN ERREUR</b>"
            for endpoint in endpoints_test["error_endpoints"][:3]:  # Limiter à 3
                emoji = self.get_status_emoji(endpoint["status"])
                report += f"\n┣━ {endpoint['endpoint']} {emoji}"
                if endpoint.get("error"):
                    error_msg = endpoint["error"][:50] + "..." if len(endpoint["error"]) > 50 else endpoint["error"]
                    report += f"\n┃  └─ {error_msg}"

        # Ajouter les endpoints lents
        if endpoints_test["slow_endpoints"]:
            report += "\n\n<b>🐌 ENDPOINTS LENTS (>2s)</b>"
            for endpoint in endpoints_test["slow_endpoints"][:3]:  # Limiter à 3
                report += f"\n┣━ {endpoint['endpoint']}: <b>{endpoint['response_time_ms']:.0f}ms</b>"

        # Réseau (si disponible)
        if "network_io" in system_metrics:
            net_io = system_metrics["network_io"]
            report += f"\n\n<b>🌐 RÉSEAU (24H)</b>"
            report += f"\n┣━ Envoyé: <b>{self.format_bytes(net_io['bytes_sent'])}</b>"
            report += f"\n┗━ Reçu: <b>{self.format_bytes(net_io['bytes_recv'])}</b>"

        report += f"\n\n<i>🤖 Rapport généré automatiquement à {datetime.now().strftime('%H:%M')}</i>"
        
        return report

    async def generate_and_send_report(self):
        """Génère et envoie le rapport quotidien de santé"""
        try:
            logger.info("Début de la génération du rapport de santé de l'application")
            
            # Collecter toutes les métriques en parallèle
            logger.info("Collecte des métriques système...")
            system_metrics_task = self.get_system_metrics()
            
            logger.info("Collecte des métriques de l'API...")
            api_metrics_task = self.get_api_health_metrics()
            
            logger.info("Test des endpoints...")
            endpoints_test_task = self.test_all_endpoints()
            
            # Attendre tous les résultats
            system_metrics, api_metrics, endpoints_test = await asyncio.gather(
                system_metrics_task,
                api_metrics_task, 
                endpoints_test_task
            )
            
            # Formater le rapport
            logger.info("Formatage du rapport...")
            report = self.format_health_report(system_metrics, api_metrics, endpoints_test)
            
            # Envoyer sur Telegram
            logger.info("Envoi du rapport sur Telegram...")
            success = self.send_telegram_message(report)
            
            if success:
                logger.info("Rapport de santé de l'application envoyé avec succès")
            else:
                logger.error("Échec de l'envoi du rapport de santé")
                
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
            # Envoyer un message d'erreur
            error_msg = f"🚨 <b>ERREUR RAPPORT SANTÉ MCP</b>\n\nImpossible de générer le rapport de santé.\nErreur: {str(e)[:100]}..."
            self.send_telegram_message(error_msg)
            return False

async def main():
    """Fonction principale"""
    try:
        # Vérifier la configuration
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Configuration Telegram manquante (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID)")
            return
        
        # Créer et exécuter le reporter
        reporter = AppHealthReporter()
        await reporter.generate_and_send_report()
        
    except Exception as e:
        logger.error(f"Erreur dans le rapport de santé de l'application: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())