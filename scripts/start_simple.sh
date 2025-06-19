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

# Configuration des variables d'environnement si nécessaire
if [ ! -f ".env" ]; then
    echo "⚙️ Configuration des variables d'environnement..."
    cat > .env << EOF
# Configuration MCP simple
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Base de données MongoDB (Hostinger)
MONGO_URL=mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true
MONGO_NAME=mcp

# Redis (Hostinger)
REDIS_HOST=d4s8888skckos8c80w4swgcw
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=20

# Configuration sécurité
SECURITY_SECRET_KEY=your_secret_key_here
SECURITY_CORS_ORIGINS=["*"]
SECURITY_ALLOWED_HOSTS=["*"]

# Configuration performance
PERF_RESPONSE_CACHE_TTL=3600
PERF_EMBEDDING_CACHE_TTL=86400
PERF_MAX_WORKERS=4

# Configuration logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ENABLE_STRUCTLOG=true
LOG_ENABLE_FILE_LOGGING=true
LOG_LOG_FILE_PATH=logs/mcp.log

# Configuration heuristiques
HEURISTIC_CENTRALITY_WEIGHT=0.4
HEURISTIC_CAPACITY_WEIGHT=0.2
HEURISTIC_REPUTATION_WEIGHT=0.2
HEURISTIC_FEES_WEIGHT=0.1
HEURISTIC_UPTIME_WEIGHT=0.1
HEURISTIC_VECTOR_WEIGHT=0.7
EOF
    echo "✅ Fichier .env créé"
fi

# Création des répertoires nécessaires
mkdir -p logs data

# Démarrage de l'application
echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"
echo ""

# Démarrage avec uvicorn
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 