#!/bin/bash
set -e
# Active l'environnement virtuel si besoin
if [ -d "/venv" ]; then
  source /venv/bin/activate
fi

# Démarrer Nginx
nginx

# Démarrer l'application FastAPI
cd /app
exec gunicorn --config /app/config/gunicorn/gunicorn.conf.py src.api.main:app 