#!/bin/bash

# Script de déploiement direct sur Hostinger
# Contourne les problèmes de connexion Docker local

set -e

echo "🚀 Déploiement direct sur Hostinger pour app.dazno.de"
echo "================================================"

# Variables de connexion Hostinger
HOSTINGER_HOST="147.79.101.32"
HOSTINGER_USER="feustey"
REMOTE_DIR="/home/feustey/mcp-production"

echo "📡 Test de connectivité vers Hostinger..."
if ! ping -c 1 $HOSTINGER_HOST >/dev/null 2>&1; then
    echo "❌ Erreur: Impossible de joindre $HOSTINGER_HOST"
    exit 1
fi

echo "✅ Connectivité OK"

echo "📦 Synchronisation du code vers le serveur..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude 'logs' \
    --exclude 'data' \
    --exclude 'node_modules' \
    ./ ${HOSTINGER_USER}@${HOSTINGER_HOST}:${REMOTE_DIR}/

echo "🔧 Déploiement sur le serveur..."
ssh ${HOSTINGER_USER}@${HOSTINGER_HOST} << 'REMOTE_SCRIPT'
cd /home/feustey/mcp-production

echo "🛑 Arrêt des services existants..."
docker-compose down || true
docker system prune -f || true

echo "📝 Mise à jour de la configuration..."
# Utiliser docker-compose.production.yml mais sans rebuild
sed -i 's/build:/# build:/g' docker-compose.production.yml || true
sed -i 's/context: ./# context: ./g' docker-compose.production.yml || true
sed -i 's/dockerfile: Dockerfile/# dockerfile: Dockerfile/g' docker-compose.production.yml || true

echo "🐳 Lancement des services de production..."
docker-compose -f docker-compose.production.yml up -d --pull always || {
    echo "❌ Erreur lors du lancement avec docker-compose, tentative alternative..."
    
    # Méthode alternative: lancement direct des conteneurs
    echo "🔄 Lancement alternatif des services..."
    
    # Créer le réseau
    docker network create mcp-network || true
    
    # Lancer Qdrant
    docker run -d --name mcp-qdrant-production \
        --network mcp-network \
        --restart unless-stopped \
        -p 127.0.0.1:6333:6333 \
        -e QDRANT__SERVICE__HTTP_PORT=6333 \
        -e QDRANT__CLUSTER__ENABLED=false \
        qdrant/qdrant:latest || true
    
    # Attendre que Qdrant soit prêt
    echo "⏳ Attente du démarrage de Qdrant..."
    sleep 10
    
    # Lancer l'API MCP avec l'image existante
    docker run -d --name mcp-api-production \
        --network mcp-network \
        --restart unless-stopped \
        -p 8000:8000 \
        -e ENVIRONMENT=production \
        -e DEBUG=false \
        -e DRY_RUN=false \
        -e LOG_LEVEL=info \
        -e HOST=0.0.0.0 \
        -e PORT=8000 \
        -e RELOAD=false \
        -e WORKERS=4 \
        -e MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true" \
        -e MONGO_NAME=mcp \
        -e REDIS_HOST=d4s8888skckos8c80w4swgcw \
        -e REDIS_PORT=6379 \
        -e REDIS_USERNAME=default \
        -e REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1 \
        -e REDIS_SSL=true \
        -e REDIS_MAX_CONNECTIONS=20 \
        -e AI_OPENAI_API_KEY="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" \
        -e AI_OPENAI_MODEL=gpt-3.5-turbo \
        -e AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small \
        -e LIGHTNING_LND_HOST=localhost:10009 \
        -e LIGHTNING_LND_REST_URL=https://127.0.0.1:8080 \
        -e LIGHTNING_USE_INTERNAL_LNBITS=false \
        -e LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits \
        -e LNBITS_INKEY=3fbbe7e0c2a24b43aa2c6ad6627f44eb \
        -e SECURITY_SECRET_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY" \
        -e SECURITY_CORS_ORIGINS='["*"]' \
        -e SECURITY_ALLOWED_HOSTS='["*"]' \
        -e PYTHONUNBUFFERED=1 \
        -e PYTHONDONTWRITEBYTECODE=1 \
        -e PYTHONPATH=/app \
        feustey/dazno:latest || true
}

echo "⏳ Attente du démarrage des services..."
sleep 15

echo "🔍 Vérification de l'état des services..."
docker ps | grep -E "(mcp-api|mcp-qdrant)" || echo "⚠️  Certains services ne sont pas visibles"

echo "🩺 Test des endpoints..."
curl -f http://localhost:8000/health || echo "⚠️  Endpoint health non accessible"
curl -f http://localhost:8000/docs || echo "⚠️  Endpoint docs non accessible"

echo "✅ Déploiement terminé!"
echo "🌐 Vérifiez: http://app.dazno.de:8000"
echo "📊 Dashboard: http://app.dazno.de:8000/docs"

REMOTE_SCRIPT

echo "🎉 Déploiement direct terminé!"
echo "🔗 Testez: http://app.dazno.de:8000/health"