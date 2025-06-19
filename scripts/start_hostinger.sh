#!/bin/bash

set -e

echo "🚀 Démarrage de MCP sur Hostinger..."

source /home/feustey/venv/bin/activate

cd /home/feustey

mkdir -p logs

exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000