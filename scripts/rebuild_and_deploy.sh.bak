#!/bin/bash
# scripts/rebuild_and_deploy.sh - Reconstruction complète et déploiement
# Dernière mise à jour: 7 janvier 2025

echo "🔨 === RECONSTRUCTION ET DÉPLOIEMENT ==="

# Variables
API_SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

# 1. Reconstruction locale
echo "🏗️ Reconstruction de l'image MCP..."
docker build -f Dockerfile.coolify -t mcp-api:latest .

echo "✅ Image construite"

# 2. Test rapide de l'image
echo "🧪 Test de l'image..."
docker run --rm mcp-api:latest python -c "import uvloop; print('✅ uvloop installé')"

# 3. Copie vers le serveur
echo "📤 Copie vers le serveur..."
docker save mcp-api:latest | gzip | ssh -i ~/.ssh/mcp_deploy_key feustey@147.79.101.32 'gunzip | sudo docker load'

# 4. Déploiement sur le serveur
echo "🚀 Déploiement sur le serveur..."
ssh -i ~/.ssh/mcp_deploy_key feustey@147.79.101.32 << 'EOF'
# Arrêter l'ancien conteneur
sudo docker stop mcp-api 2>/dev/null || true
sudo docker rm mcp-api 2>/dev/null || true

# Créer le fichier .env avec les bonnes variables
cat > /tmp/mcp.env << 'ENVEOF'
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
RELOAD=false
WORKERS=2
MONGO_URL=mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true
MONGO_NAME=mcp
REDIS_HOST=d4s8888skckos8c80w4swgcw
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=20
AI_OPENAI_API_KEY=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
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SECURITY_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY
SECURITY_CORS_ORIGINS=["*"]
SECURITY_ALLOWED_HOSTS=["*"]
PERF_RESPONSE_CACHE_TTL=3600
PERF_EMBEDDING_CACHE_TTL=86400
PERF_MAX_WORKERS=4
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ENABLE_STRUCTLOG=true
LOG_ENABLE_FILE_LOGGING=true
LOG_LOG_FILE_PATH=logs/mcp.log
HEURISTIC_CENTRALITY_WEIGHT=0.4
HEURISTIC_CAPACITY_WEIGHT=0.2
HEURISTIC_REPUTATION_WEIGHT=0.2
HEURISTIC_FEES_WEIGHT=0.1
HEURISTIC_UPTIME_WEIGHT=0.1
HEURISTIC_VECTOR_WEIGHT=0.7
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=/app
ENVEOF

# Démarrer le nouveau conteneur
sudo docker run -d --name mcp-api --restart unless-stopped \
  -p 8000:8000 \
  --env-file /tmp/mcp.env \
  -v /var/log/mcp:/app/logs \
  mcp-api:latest

echo "✅ Conteneur redémarré"
sudo docker ps | grep mcp-api
EOF

echo "✅ Déploiement terminé"

# 5. Test final
echo "🔍 Tests finaux..."
sleep 10

curl -f http://147.79.101.32:8000/health && echo "✅ API accessible directement"
curl -f https://api.dazno.de/health && echo "✅ API accessible via le domaine"

echo "🎯 Testez maintenant :"
echo "• http://147.79.101.32:8000/health"
echo "• https://api.dazno.de/health (après quelques minutes)" 