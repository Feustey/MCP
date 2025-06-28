#!/bin/bash

# Script de déploiement complet pour MCP
# Dernière mise à jour: 7 mai 2025

set -e

echo "🚀 Démarrage du déploiement MCP..."

# 1. Vérification des prérequis
echo "🔍 Vérification des prérequis..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker n'est pas installé"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose n'est pas installé"; exit 1; }

# 2. Configuration de l'environnement
echo "⚙️ Configuration de l'environnement..."
if [ ! -f .env ]; then
    echo "❌ Fichier .env manquant"
    exit 1
fi

# 3. Sauvegarde de la configuration actuelle
echo "💾 Sauvegarde de la configuration actuelle..."
timestamp=$(date +%Y%m%d_%H%M%S)
backup_dir="backups/${timestamp}"
mkdir -p "$backup_dir"
if [ -d "data" ]; then
    tar -czf "${backup_dir}/data_backup.tar.gz" data/
fi

# 4. Arrêt des services existants
echo "🛑 Arrêt des services existants..."
docker-compose -f docker-compose.hostinger-local.yml down || true

# 5. Nettoyage des volumes si nécessaire
read -p "❓ Voulez-vous nettoyer les volumes existants ? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Nettoyage des volumes..."
    docker volume rm $(docker volume ls -q | grep mcp) || true
fi

# 6. Construction des images
echo "🏗️ Construction des images Docker..."
docker build -t mcp-api:latest -f Dockerfile.api .

# 7. Démarrage des services
echo "▶️ Démarrage des services..."
docker-compose -f docker-compose.hostinger-local.yml up -d

# 8. Vérification de la santé des services
echo "🏥 Vérification de la santé des services..."
sleep 10

check_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo "  Vérification de $service..."
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.hostinger-local.yml ps $service | grep -q "Up"; then
            echo "  ✅ $service est opérationnel"
            return 0
        fi
        echo "  ⏳ Tentative $attempt/$max_attempts..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "  ❌ $service n'a pas démarré correctement"
    return 1
}

check_service mongodb
check_service redis
check_service mcp-api
check_service nginx

# 9. Vérification des endpoints
echo "🔌 Vérification des endpoints..."
curl -f http://localhost/health || { echo "❌ Endpoint /health non accessible"; exit 1; }

# 10. Configuration des sauvegardes automatiques
echo "📦 Configuration des sauvegardes automatiques..."
if [ ! -f config/backup/crontab ]; then
    echo "0 */6 * * * /app/backup.sh" > config/backup/crontab
fi

# 11. Mise en place du monitoring
echo "📊 Configuration du monitoring..."
docker-compose -f docker-compose.hostinger-local.yml exec -T mongodb mongosh --eval "db.serverStatus()"
docker-compose -f docker-compose.hostinger-local.yml exec -T redis redis-cli info

echo "✅ Déploiement terminé avec succès!"
echo "📝 Logs disponibles dans: docker-compose -f docker-compose.hostinger-local.yml logs -f"
echo "🌍 API accessible sur: http://localhost/" 