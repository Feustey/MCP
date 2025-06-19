#!/bin/sh

# Script de démarrage simple pour MCP (sans Docker)
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Démarrage simple de MCP..."

# Vérification de Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 n'est pas installé"
    exit 1
fi

# Vérification des dépendances
echo "🔍 Vérification des dépendances..."
if ! python3 -c "import fastapi, pydantic, uvicorn" 2>/dev/null; then
    echo "❌ Dépendances manquantes. Installation..."
    pip3 install -r requirements-hostinger.txt
fi

# Configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."

# Export direct des variables d'environnement
export ENVIRONMENT=production
export DEBUG=false
export DRY_RUN=true
export LOG_LEVEL=INFO

# Configuration serveur
export HOST=0.0.0.0
export PORT=8000
export RELOAD=false

# Base de données MongoDB (Hostinger)
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export MONGO_NAME=mcp

# Redis (Hostinger)
export REDIS_HOST=d4s8888skckos8c80w4swgcw
export REDIS_PORT=6379
export REDIS_USERNAME=default
export REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1
export REDIS_SSL=true
export REDIS_MAX_CONNECTIONS=20

# Configuration sécurité
export SECURITY_SECRET_KEY=your_secret_key_here
export SECURITY_CORS_ORIGINS='["*"]'
export SECURITY_ALLOWED_HOSTS='["*"]'

# Configuration performance
export PERF_RESPONSE_CACHE_TTL=3600
export PERF_EMBEDDING_CACHE_TTL=86400
export PERF_MAX_WORKERS=4

# Configuration logging
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export LOG_ENABLE_STRUCTLOG=true
export LOG_ENABLE_FILE_LOGGING=true
export LOG_LOG_FILE_PATH=logs/mcp.log

# Configuration heuristiques
export HEURISTIC_CENTRALITY_WEIGHT=0.4
export HEURISTIC_CAPACITY_WEIGHT=0.2
export HEURISTIC_REPUTATION_WEIGHT=0.2
export HEURISTIC_FEES_WEIGHT=0.1
export HEURISTIC_UPTIME_WEIGHT=0.1
export HEURISTIC_VECTOR_WEIGHT=0.7

echo "✅ Variables d'environnement configurées"

# Création des répertoires nécessaires
mkdir -p logs data

# Test de la configuration
echo "🧪 Test de la configuration..."
python3 -c "
import os
print('MONGO_URL:', os.getenv('MONGO_URL'))
print('REDIS_HOST:', os.getenv('REDIS_HOST'))
print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))
"

# Démarrage de l'application
echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"
echo ""

# Démarrage avec uvicorn
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 