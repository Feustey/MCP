#!/bin/bash

set -e

echo "🚀 Démarrage de MCP en arrière-plan..."

source /home/feustey/venv/bin/activate

cd /home/feustey

mkdir -p logs

pkill -f "uvicorn src.api.main:app" || true

nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &

sleep 3

if pgrep -f "uvicorn src.api.main:app" > /dev/null; then
    echo "✅ Application démarrée!"
else
    echo "❌ Échec du démarrage"
    exit 1
fi