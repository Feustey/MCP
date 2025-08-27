#!/usr/bin/env python3
import os
import requests
import socket
import platform
import json
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
HEARTBEAT_URL = os.getenv("HEARTBEAT_URL", "https://your-central-server.com/api/heartbeat")
INSTANCE_ID = os.getenv("INSTANCE_ID") or socket.gethostname()
MCP_VERSION = os.getenv("MCP_VERSION", "0.1.0-beta")
LOG_PATH = os.getenv("MCP_LOG_PATH", "logs/fee_optimizer.log")

# Récupérer les 20 dernières lignes du log
def get_recent_logs(log_path, n=20):
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception:
        return ""

def send_heartbeat():
    payload = {
        "instance_id": INSTANCE_ID,
        "version": MCP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "status": "online",
        "recent_logs": get_recent_logs(LOG_PATH),
    }
    try:
        resp = requests.post(HEARTBEAT_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"Heartbeat envoyé avec succès à {HEARTBEAT_URL}")
        else:
            print(f"Erreur lors de l'envoi du heartbeat: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Exception lors de l'envoi du heartbeat: {e}")

if __name__ == "__main__":
    send_heartbeat() 