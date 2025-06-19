#!/bin/bash

# Script de configuration des bases de données Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🗄️ Configuration des bases de données Hostinger..."

# Variables pour les bases de données Hostinger
REDIS_URL="redis://default:YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1@d4s8888skckos8c80w4swgcw:6379/0"
MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"

# Extraction des composants Redis
REDIS_HOST=$(echo $REDIS_URL | sed 's|redis://default:.*@\([^:]*\):.*|\1|')
REDIS_PORT=$(echo $REDIS_URL | sed 's|redis://default:.*@[^:]*:\([^/]*\)/.*|\1|')
REDIS_PASSWORD=$(echo $REDIS_URL | sed 's|redis://default:\([^@]*\)@.*|\1|')

# Extraction des composants MongoDB
MONGO_HOST=$(echo $MONGO_URL | sed 's|mongodb://root:.*@\([^:]*\):.*|\1|')
MONGO_PORT=$(echo $MONGO_URL | sed 's|mongodb://root:.*@[^:]*:\([^/?]*\).*|\1|')
MONGO_PASSWORD=$(echo $MONGO_URL | sed 's|mongodb://root:\([^@]*\)@.*|\1|')

echo "📋 Configuration détectée:"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
echo "  MongoDB: $MONGO_HOST:$MONGO_PORT"

# Création du fichier .env avec les configurations Hostinger
cat > .env << EOF
# Configuration MCP pour Hostinger
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Base de données MongoDB (Hostinger)
MONGO_URL=$MONGO_URL
MONGO_NAME=mcp

# Redis (Hostinger)
REDIS_HOST=$REDIS_HOST
REDIS_PORT=$REDIS_PORT
REDIS_USERNAME=default
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=20

# Configuration IA (optionnel)
AI_OPENAI_API_KEY=your_openai_key_here
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuration Lightning (optionnel)
LIGHTNING_LND_HOST=localhost:10009
LIGHTNING_LND_REST_URL=https://127.0.0.1:8080
LIGHTNING_USE_INTERNAL_LNBITS=true
LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits

# Configuration sécurité
SECURITY_SECRET_KEY=$(openssl rand -hex 32)
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

echo "✅ Fichier .env créé avec les configurations Hostinger"

# Test de connectivité Redis
echo "🔍 Test de connectivité Redis..."
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping >/dev/null 2>&1; then
        echo "✅ Redis: Connexion réussie"
    else
        echo "⚠️ Redis: Impossible de se connecter (redis-cli non disponible ou connexion échouée)"
    fi
else
    echo "ℹ️ Redis: redis-cli non disponible, test de connectivité ignoré"
fi

# Test de connectivité MongoDB
echo "🔍 Test de connectivité MongoDB..."
if command -v mongosh >/dev/null 2>&1; then
    if mongosh "$MONGO_URL" --eval "db.runCommand('ping')" >/dev/null 2>&1; then
        echo "✅ MongoDB: Connexion réussie"
    else
        echo "⚠️ MongoDB: Impossible de se connecter (mongosh non disponible ou connexion échouée)"
    fi
else
    echo "ℹ️ MongoDB: mongosh non disponible, test de connectivité ignoré"
fi

echo ""
echo "🎉 Configuration des bases de données terminée!"
echo ""
echo "📝 Pour tester l'application:"
echo "   python3 -c \"from config import settings; print('Configuration chargée:', settings.database.url)\""
echo ""
echo "🚀 Pour démarrer l'application:"
echo "   uvicorn src.api.main:app --host 0.0.0.0 --port 8000" 