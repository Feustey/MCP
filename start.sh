#!/bin/bash
set -e
# Active l'environnement virtuel si besoin
if [ -d "/venv" ]; then
  source /venv/bin/activate
fi
# Lance l'application FastAPI (adapter si besoin)
exec python3.9 server.py 