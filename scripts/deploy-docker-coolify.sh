#!/bin/bash
# scripts/deploy-docker-coolify.sh - Déploiement Docker + Coolify pour Hostinger
# Dernière mise à jour: 27 mai 2025

set -e

# Variables de configuration
IMAGE_NAME="mcp-api"
TAG="latest"
COOLIFY_URL="https://votre-coolify.hostinger.com"  # À adapter avec votre URL Coolify

echo "🚀 Déploiement Docker + Coolify pour MCP"
echo "======================================"

# 1. Vérification des prérequis
echo "📋 Vérification des prérequis..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

# 2. Construction de l'image
echo "🔨 Construction de l'image Docker..."
docker build -f Dockerfile.coolify -t ${IMAGE_NAME}:${TAG} .

# 3. Test rapide de l'image
echo "🧪 Test rapide de l'image..."
docker run --rm ${IMAGE_NAME}:${TAG} python -c "print('✅ Image OK')"

# 4. Instructions pour Coolify
echo "📝 Instructions pour le déploiement Coolify :"
echo "1. Connectez-vous à votre dashboard Coolify : ${COOLIFY_URL}"
echo "2. Créez un nouveau service avec les paramètres suivants :"
echo "   - Image : ${IMAGE_NAME}:${TAG}"
echo "   - Port : 8000"
echo "   - Variables d'environnement requises :"
echo "     MONGO_URL=mongodb://mongodb:27017/mcp"
echo "     REDIS_HOST=redis"
echo "     REDIS_PORT=6379"
echo "     AI_OPENAI_API_KEY=votre_clé"
echo "     SECURITY_SECRET_KEY=votre_clé"
echo "3. Connectez le service au réseau 'hostinger-network'"
echo "4. Démarrez le service"

echo "✅ Image prête pour le déploiement"
echo "📚 Consultez docs/deploy-coolify-guide.md pour plus de détails" 