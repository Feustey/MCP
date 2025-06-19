#!/bin/sh

# Script de démarrage simple pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage simple de MCP..."

# Vérification des dépendances
echo "🔍 Vérification des dépendances..."
python3 -c "import fastapi, uvicorn, pymongo, redis" 2>/dev/null || {
    echo "❌ Dépendances manquantes. Installation..."
    pip install -r requirements-hostinger.txt
}

# Configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."

# Variables principales
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"
export ENVIRONMENT="production"
export DRY_RUN="true"

# Variables AI requises
export AI_OPENAI_API_KEY="your_openai_api_key_here"
export AI_OPENAI_MODEL="gpt-3.5-turbo"
export AI_OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

# Variables de sécurité requises
export SECURITY_SECRET_KEY="your_secret_key_here_change_this_in_production"
export SECURITY_CORS_ORIGINS='["*"]'
export SECURITY_ALLOWED_HOSTS='["*"]'

# Variables Lightning
export LIGHTNING_LND_HOST="localhost:10009"
export LIGHTNING_LND_REST_URL="https://127.0.0.1:8080"
export LIGHTNING_USE_INTERNAL_LNBITS="true"
export LIGHTNING_LNBITS_URL="http://127.0.0.1:8000/lnbits"

# Variables de performance
export PERF_RESPONSE_CACHE_TTL="3600"
export PERF_EMBEDDING_CACHE_TTL="86400"
export PERF_MAX_WORKERS="4"

# Variables de logging
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"
export LOG_ENABLE_STRUCTLOG="true"
export LOG_ENABLE_FILE_LOGGING="true"
export LOG_LOG_FILE_PATH="logs/mcp.log"

# Variables d'heuristiques
export HEURISTIC_CENTRALITY_WEIGHT="0.4"
export HEURISTIC_CAPACITY_WEIGHT="0.2"
export HEURISTIC_REPUTATION_WEIGHT="0.2"
export HEURISTIC_FEES_WEIGHT="0.1"
export HEURISTIC_UPTIME_WEIGHT="0.1"
export HEURISTIC_VECTOR_WEIGHT="0.7"

echo "✅ Variables d'environnement configurées"

# Test de la configuration
echo "🧪 Test de la configuration..."
python3 scripts/test_config.py
if [ $? -ne 0 ]; then
    echo "❌ Configuration échouée"
    exit 1
fi

echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"

# Démarrage de l'application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 