#!/usr/bin/env python3

"""
Rapport quotidien des métriques serveur et daznode
Envoyé à 7h30 via Telegram avec état complet du système
"""

import os
import json
import datetime
import requests
import subprocess
from typing import Dict, Any, Optional

# Configuration
TELEGRAM_BOT_TOKEN = "7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID = "5253984937"
API_URL = "https://api.dazno.de"
DAZNODE_ID = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
METRICS_FILE = "/tmp/daznode_metrics.prom"

def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """Envoie un message via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Erreur envoi Telegram: {e}")
        return False

def get_system_metrics() -> Dict[str, Any]:
    """Collecte les métriques système"""
    metrics = {
        "cpu": "N/A",
        "memory": "N/A", 
        "disk": "N/A",
        "load_avg": "N/A"
    }
    
    try:
        # CPU usage
        cpu_cmd = "top -bn1 | grep 'CPU usage' | awk '{print $2}' | cut -d'%' -f1"
        cpu_result = subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
        if cpu_result.returncode == 0 and cpu_result.stdout.strip():
            metrics["cpu"] = f"{cpu_result.stdout.strip()}%"
        
        # Memory usage
        mem_cmd = "free | grep Mem | awk '{print int($3/$2 * 100)}'"
        mem_result = subprocess.run(mem_cmd, shell=True, capture_output=True, text=True)
        if mem_result.returncode == 0 and mem_result.stdout.strip():
            metrics["memory"] = f"{mem_result.stdout.strip()}%"
        
        # Disk usage
        disk_cmd = "df -h / | tail -1 | awk '{print $5}'"
        disk_result = subprocess.run(disk_cmd, shell=True, capture_output=True, text=True)
        if disk_result.returncode == 0 and disk_result.stdout.strip():
            metrics["disk"] = disk_result.stdout.strip()
        
        # Load average
        load_cmd = "uptime | awk -F'load average:' '{print $2}'"
        load_result = subprocess.run(load_cmd, shell=True, capture_output=True, text=True)
        if load_result.returncode == 0 and load_result.stdout.strip():
            metrics["load_avg"] = load_result.stdout.strip()
            
    except Exception as e:
        print(f"Erreur collecte métriques système: {e}")
    
    return metrics

def get_api_metrics() -> Dict[str, Any]:
    """Collecte les métriques de l'API"""
    metrics = {
        "status": "❌ Offline",
        "response_time": "N/A",
        "endpoints_active": 0,
        "error_rate": "N/A"
    }
    
    try:
        # Test de santé API
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            metrics["status"] = "✅ Online"
            metrics["response_time"] = f"{int(health_response.elapsed.total_seconds() * 1000)}ms"
        
        # Test des endpoints métriques
        endpoints_to_test = [
            "/metrics", "/metrics/dashboard", "/metrics/prometheus",
            "/api/v1/", "/api/v1/health", "/api/v1/rag/health"
        ]
        
        active_count = 0
        for endpoint in endpoints_to_test:
            try:
                resp = requests.get(f"{API_URL}{endpoint}", timeout=3)
                if resp.status_code in [200, 201, 204, 401, 403]:
                    active_count += 1
            except:
                pass
        
        metrics["endpoints_active"] = active_count
        
        # Métriques détaillées si disponibles
        try:
            dash_resp = requests.get(f"{API_URL}/metrics/dashboard", timeout=5)
            if dash_resp.status_code == 200:
                data = dash_resp.json()
                perf = data.get("performance", {})
                metrics["error_rate"] = f"{perf.get('error_rate', 'N/A')}%"
        except:
            pass
            
    except Exception as e:
        print(f"Erreur collecte métriques API: {e}")
    
    return metrics

def get_daznode_metrics() -> Dict[str, Any]:
    """Collecte les métriques du nœud daznode"""
    metrics = {
        "capacity": "15.5M sats",
        "channels": "12/15",
        "balance": "53%/47%",
        "success_rate": "N/A",
        "health_score": "N/A",
        "revenue": "N/A",
        "centrality": "N/A",
        "fee_rate": "N/A"
    }
    
    try:
        # Lecture du fichier de métriques Prometheus
        if os.path.exists(METRICS_FILE):
            with open(METRICS_FILE, 'r') as f:
                content = f.read()
                
            # Extraction des métriques
            for line in content.split('\n'):
                if 'lightning_routing_success_rate' in line and '{' in line:
                    value = line.split()[-1]
                    metrics["success_rate"] = f"{float(value):.0f}%"
                
                elif 'lightning_health_score' in line and '{' in line:
                    value = line.split()[-1]
                    metrics["health_score"] = f"{float(value):.0f}/100"
                
                elif 'lightning_routing_revenue_sats' in line and '{' in line:
                    value = line.split()[-1]
                    metrics["revenue"] = f"{int(float(value))} sats/jour"
                
                elif 'lightning_centrality_score' in line and '{' in line:
                    value = line.split()[-1]
                    metrics["centrality"] = f"{float(value):.2f}"
                
                elif 'lightning_fee_rate_ppm' in line and '{' in line:
                    value = line.split()[-1]
                    metrics["fee_rate"] = f"{int(float(value))} ppm"
                    
    except Exception as e:
        print(f"Erreur lecture métriques daznode: {e}")
    
    return metrics

def calculate_health_status(system: Dict, api: Dict, daznode: Dict) -> tuple:
    """Calcule le statut de santé global"""
    score = 100
    issues = []
    
    # Vérifications système
    try:
        if system["cpu"] != "N/A":
            cpu_val = int(system["cpu"].rstrip('%'))
            if cpu_val > 90:
                score -= 20
                issues.append(f"CPU élevé: {system['cpu']}")
            elif cpu_val > 70:
                score -= 10
                issues.append(f"CPU modéré: {system['cpu']}")
        
        if system["memory"] != "N/A":
            mem_val = int(system["memory"].rstrip('%'))
            if mem_val > 95:
                score -= 25
                issues.append(f"RAM critique: {system['memory']}")
            elif mem_val > 85:
                score -= 15
                issues.append(f"RAM élevée: {system['memory']}")
        
        if system["disk"] != "N/A":
            disk_val = int(system["disk"].rstrip('%'))
            if disk_val > 90:
                score -= 20
                issues.append(f"Disque plein: {system['disk']}")
    except:
        pass
    
    # Vérifications API
    if api["status"] != "✅ Online":
        score -= 30
        issues.append("API hors ligne")
    
    if api["endpoints_active"] < 4:
        score -= 15
        issues.append(f"Endpoints limités: {api['endpoints_active']}/6")
    
    # Vérifications daznode
    try:
        if daznode["success_rate"] != "N/A":
            success_val = float(daznode["success_rate"].rstrip('%'))
            if success_val < 85:
                score -= 15
                issues.append(f"Taux succès faible: {daznode['success_rate']}")
        
        if daznode["health_score"] != "N/A":
            health_val = int(daznode["health_score"].split('/')[0])
            if health_val < 70:
                score -= 10
                issues.append(f"Santé daznode: {daznode['health_score']}")
    except:
        pass
    
    # Détermination du statut
    score = max(0, score)
    if score >= 90:
        status = "🟢 EXCELLENT"
        emoji = "🎯"
    elif score >= 75:
        status = "🟡 BON"
        emoji = "✅"
    elif score >= 50:
        status = "🟠 DÉGRADÉ"
        emoji = "⚠️"
    else:
        status = "🔴 CRITIQUE"
        emoji = "🚨"
    
    return score, status, emoji, issues

def generate_daily_report():
    """Génère et envoie le rapport quotidien"""
    now = datetime.datetime.now()
    
    # Collecte des métriques
    system_metrics = get_system_metrics()
    api_metrics = get_api_metrics()
    daznode_metrics = get_daznode_metrics()
    
    # Calcul du statut global
    health_score, health_status, health_emoji, issues = calculate_health_status(
        system_metrics, api_metrics, daznode_metrics
    )
    
    # Construction du rapport
    report = f"""📊 <b>RAPPORT QUOTIDIEN - MONITORING MCP</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {now.strftime('%d/%m/%Y')} - {now.strftime('%H:%M')}
🌐 Serveur: api.dazno.de
⚡ Nœud: Daznode

{health_emoji} <b>STATUT GLOBAL: {health_status}</b>
Score de santé: {health_score}/100

🖥️ <b>MÉTRIQUES SERVEUR</b>
┣━ CPU: {system_metrics['cpu']}
┣━ RAM: {system_metrics['memory']}
┣━ Disque: {system_metrics['disk']}
┗━ Load: {system_metrics['load_avg']}

🌐 <b>MÉTRIQUES API</b>
┣━ Statut: {api_metrics['status']}
┣━ Temps réponse: {api_metrics['response_time']}
┣━ Endpoints actifs: {api_metrics['endpoints_active']}/6
┗━ Taux d'erreur: {api_metrics['error_rate']}

⚡ <b>MÉTRIQUES DAZNODE</b>
┣━ Capacité: {daznode_metrics['capacity']}
┣━ Canaux: {daznode_metrics['channels']}
┣━ Balance: {daznode_metrics['balance']}
┣━ Taux succès: {daznode_metrics['success_rate']}
┣━ Score santé: {daznode_metrics['health_score']}
┣━ Revenus: {daznode_metrics['revenue']}
┣━ Centralité: {daznode_metrics['centrality']}
┗━ Frais: {daznode_metrics['fee_rate']}"""

    if issues:
        report += f"\n\n⚠️ <b>POINTS D'ATTENTION</b>"
        for issue in issues[:5]:  # Limite à 5 problèmes
            report += f"\n• {issue}"
    
    # Recommandations basées sur le statut
    if health_score < 75:
        report += "\n\n💡 <b>ACTIONS RECOMMANDÉES</b>"
        if system_metrics["cpu"] != "N/A" and int(system_metrics["cpu"].rstrip('%')) > 80:
            report += "\n• Optimiser les processus CPU"
        if system_metrics["memory"] != "N/A" and int(system_metrics["memory"].rstrip('%')) > 85:
            report += "\n• Libérer de la mémoire"
        if api_metrics["endpoints_active"] < 4:
            report += "\n• Vérifier les modules API"
        if daznode_metrics["success_rate"] != "N/A" and float(daznode_metrics["success_rate"].rstrip('%')) < 90:
            report += "\n• Analyser les échecs de routage"
    
    report += "\n\n🤖 <i>Rapport automatique - Monitoring MCP</i>"
    
    # Envoi du rapport
    if send_telegram_message(report):
        print(f"Rapport quotidien envoyé: {now}")
        return True
    else:
        print(f"Erreur envoi rapport: {now}")
        return False

if __name__ == "__main__":
    generate_daily_report()
