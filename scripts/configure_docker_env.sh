#!/bin/sh

# Script de configuration des variables d'environnement pour Docker
# Dernière mise à jour: 9 mai 2025

set -e

echo "🐳 Configuration des variables d'environnement pour Docker..."

# Variables pour les bases de données Hostinger
REDIS_URL="redis://default:YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1@d4s8888skckos8c80w4swgcw:6379/0"
MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"

# Extraction des composants Redis
REDIS_HOST=$(echo $REDIS_URL | sed 's|redis://default:.*@\([^:]*\):.*|\1|')
REDIS_PORT=$(echo $REDIS_URL | sed 's|redis://default:.*@[^:]*:\([^/]*\)/.*|\1|')
REDIS_PASSWORD=$(echo $REDIS_URL | sed 's|redis://default:\([^@]*\)@.*|\1|')

echo "📋 Configuration détectée:"
echo "  Redis: $REDIS_HOST:$REDIS_PORT"
echo "  MongoDB: $MONGO_URL"

# Création du fichier .env pour Docker
cat > .env.docker << EOF
# Configuration MCP pour Docker avec Hostinger
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

echo "✅ Fichier .env.docker créé avec les configurations Hostinger"

echo ""
echo "🚀 Pour démarrer avec Docker Compose:"
echo "   docker-compose --env-file .env.docker up -d"
echo ""
echo "🔧 Ou pour démarrer manuellement:"
echo "   docker run --env-file .env.docker -p 8000:8000 mcp-api:latest" 