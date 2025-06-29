#!/bin/bash

set -e

# Configuration
REMOTE_USER="root"
REMOTE_HOST="api.dazno.de"
REMOTE_DIR="/opt/mcp"
DOCKER_COMPOSE_FILE="docker-compose.hostinger.prod.yml"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

echo "🚀 Déploiement MCP sur Hostinger..."

# Création du répertoire de backup local
mkdir -p $BACKUP_DIR

# Sauvegarde des données existantes sur le serveur distant
echo "📦 Sauvegarde des données existantes..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    if [ -d data ]; then tar czf - data | base64; fi" | base64 -d > $BACKUP_DIR/data_backup.tar.gz
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    if [ -d config ]; then tar czf - config | base64; fi" | base64 -d > $BACKUP_DIR/config_backup.tar.gz
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    if [ -d logs ]; then tar czf - logs | base64; fi" | base64 -d > $BACKUP_DIR/logs_backup.tar.gz

# Construction des images Docker
echo "🏗️ Construction des images Docker..."
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

# Sauvegarde des images Docker
echo "💾 Sauvegarde des images Docker..."
docker save mcp-api:latest | gzip > $BACKUP_DIR/mcp-api.tar.gz

# Transfert des fichiers vers le serveur distant
echo "📤 Transfert des fichiers vers le serveur..."
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"
scp $DOCKER_COMPOSE_FILE $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
scp .env $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
scp gunicorn.conf.py $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
scp $BACKUP_DIR/mcp-api.tar.gz $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

# Chargement des images sur le serveur distant
echo "📥 Chargement des images sur le serveur..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    docker load < mcp-api.tar.gz && \
    rm mcp-api.tar.gz"

# Déploiement sur le serveur distant
echo "🚀 Déploiement sur le serveur..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    docker-compose -f $DOCKER_COMPOSE_FILE down --remove-orphans && \
    docker-compose -f $DOCKER_COMPOSE_FILE up -d"

# Vérification du déploiement
echo "🔍 Vérification du déploiement..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
    docker-compose -f $DOCKER_COMPOSE_FILE ps && \
    docker-compose -f $DOCKER_COMPOSE_FILE logs --tail=50"

# Nettoyage local
echo "🧹 Nettoyage local..."
docker system prune -f

echo "✅ Déploiement terminé avec succès!"
echo "📝 Logs disponibles dans: $BACKUP_DIR"
echo "🌐 API accessible sur: https://api.dazno.de"
echo "📊 Grafana accessible sur: https://api.dazno.de/grafana" 