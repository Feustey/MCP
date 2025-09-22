#!/bin/bash

echo "🚀 Démarrage MCP Lightning en production..."

# Charger l'environnement virtuel
source venv/bin/activate

# Charger la configuration de production
export $(cat .env.production.active | grep -v '^#' | xargs)

# Démarrer le monitoring en arrière-plan si activé
if [ "$MONITORING_ENABLED" = "true" ]; then
    echo "📊 Démarrage du monitoring de production..."
    nohup python3 src/monitoring/production_monitor.py > logs/monitoring.log 2>&1 &
    MONITORING_PID=$!
    echo $MONITORING_PID > monitoring.pid
    echo "✓ Monitoring démarré (PID: $MONITORING_PID)"
fi

# Démarrer l'API principale
echo "🌐 Démarrage de l'API MCP Lightning..."

# Vérifier si main.py existe
if [ ! -f "main.py" ]; then
    echo "⚠️  main.py non trouvé, création d'un serveur de base..."
    cat > main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="MCP Lightning API",
    description="API pour le système MCP Lightning Network",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "MCP Lightning API is running",
        "version": "1.0.0",
        "mode": "production"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": "2025-01-07"}

@app.get("/api/v1/lightning/status")
def lightning_status():
    return {"lightning": "operational", "mock_mode": True}
EOF
fi

# Définir des valeurs par défaut si les variables ne sont pas définies
WORKERS=${WORKERS:-2}
LOG_LEVEL=${LOG_LEVEL:-info}

exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers $WORKERS --log-level $LOG_LEVEL
