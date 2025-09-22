#!/bin/bash

echo "⏹️  Arrêt MCP Lightning..."

# Arrêter le monitoring
if [ -f "monitoring.pid" ]; then
    MONITORING_PID=$(cat monitoring.pid)
    echo "Arrêt du monitoring (PID: $MONITORING_PID)..."
    kill $MONITORING_PID 2>/dev/null
    rm -f monitoring.pid
fi

# Arrêter l'API principale
pkill -f "uvicorn main:app"

echo "✓ Services arrêtés"
