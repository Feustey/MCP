#!/bin/bash

echo "🚀 Déploiement API optimisée"

# Variables
SERVER="feustey@147.79.101.32"
DEPLOY_PATH="/home/feustey/mcp-production"

# 1. Test de connectivité
echo "Test de connexion au serveur..."
if ! ssh -o ConnectTimeout=10 $SERVER "echo 'Connexion OK'"; then
    echo "❌ Impossible de se connecter au serveur"
    exit 1
fi

# 2. Copie des configurations
echo "Copie des configurations optimisées..."
scp config/nginx/api-optimized.conf $SERVER:$DEPLOY_PATH/config/nginx/
scp config/redis_cache.conf $SERVER:$DEPLOY_PATH/config/
scp app/core/performance_config.py $SERVER:$DEPLOY_PATH/app/core/

# 3. Restart des services
echo "Redémarrage des services..."
ssh $SERVER << 'REMOTE'
cd /home/feustey/mcp-production

# Backup configuration actuelle
cp docker-compose.yml docker-compose.backup.yml

# Update Docker Compose avec optimisations
docker-compose down
docker-compose pull
docker-compose up -d --scale mcp-api=2

# Vérification
sleep 10
docker-compose ps
curl -I http://localhost:8000/docs

# Restart Nginx avec nouvelle config
docker-compose exec nginx nginx -s reload
REMOTE

echo "✅ Déploiement terminé"
