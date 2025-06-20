#!/bin/bash

# Script de build et push vers Docker Hub
# Dernière mise à jour: 7 janvier 2025

set -e

# Configuration
DOCKER_IMAGE="feustey/dazno"
DOCKER_TAG="latest"
DOCKERFILE="Dockerfile.hub"

echo "🚀 Build et push de l'image Docker vers Docker Hub"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
log_info "Vérification des prérequis..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé"
    exit 1
fi

# Vérifier que Docker est en cours d'exécution
if ! docker info > /dev/null 2>&1; then
    log_error "Docker n'est pas accessible"
    exit 1
fi

log_info "✅ Prérequis vérifiés"

# Vérification de la connexion Docker Hub
log_info "Vérification de la connexion Docker Hub..."

# Test de connexion à Docker Hub
if ! docker pull hello-world:latest > /dev/null 2>&1; then
    log_warn "Impossible de se connecter à Docker Hub, tentative de login..."
    docker login
fi

# Nettoyage des images précédentes
log_info "Nettoyage des images précédentes..."
docker rmi ${DOCKER_IMAGE}:${DOCKER_TAG} 2>/dev/null || true

# Build de l'image
log_info "🔨 Build de l'image Docker..."
docker build -f ${DOCKERFILE} -t ${DOCKER_IMAGE}:${DOCKER_TAG} .

if [ $? -ne 0 ]; then
    log_error "❌ Échec du build Docker"
    exit 1
fi

log_info "✅ Build réussi"

# Test de l'image
log_info "🧪 Test de l'image..."

# Création d'un réseau de test
docker network create mcp-test 2>/dev/null || true

# Démarrage du conteneur de test
log_info "Démarrage du conteneur de test..."
docker run --rm -d \
    --name mcp-test \
    --network mcp-test \
    -p 8000:8000 \
    -e MONGO_URL=mongodb://test:test@localhost:27017/test \
    -e REDIS_HOST=localhost \
    -e REDIS_PASSWORD=test \
    -e AI_OPENAI_API_KEY=dummykey \
    -e LNBITS_INKEY=dummylnbitskey \
    -e SECURITY_SECRET_KEY=dummysecretkey \
    ${DOCKER_IMAGE}:${DOCKER_TAG}

# Attendre que le conteneur démarre
log_info "Attente du démarrage du conteneur..."
sleep 15

# Test de santé
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_info "✅ Test de santé réussi"
else
    log_error "❌ Test de santé échoué"
    docker logs mcp-test
    docker stop mcp-test
    docker network rm mcp-test
    exit 1
fi

# Test des endpoints principaux
log_info "Test des endpoints principaux..."

# Test de la documentation
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    log_info "✅ Endpoint /docs accessible"
else
    log_warn "⚠️ Endpoint /docs non accessible"
fi

# Test de l'API
if curl -f http://localhost:8000/api/v1/simulate/profiles > /dev/null 2>&1; then
    log_info "✅ Endpoint /api/v1/simulate/profiles accessible"
else
    log_warn "⚠️ Endpoint /api/v1/simulate/profiles non accessible"
fi

# Arrêt du conteneur de test
log_info "Arrêt du conteneur de test..."
docker stop mcp-test
docker network rm mcp-test

log_info "✅ Tests terminés avec succès"

# Push vers Docker Hub
log_info "📤 Push vers Docker Hub..."
docker push ${DOCKER_IMAGE}:${DOCKER_TAG}

if [ $? -ne 0 ]; then
    log_error "❌ Échec du push vers Docker Hub"
    exit 1
fi

log_info "✅ Image publiée avec succès sur Docker Hub!"
echo ""
echo "📋 Informations de publication:"
echo "   🐳 Image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
echo "   🔗 URL: https://hub.docker.com/r/feustey/dazno"
echo "   📊 Taille: $(docker images ${DOCKER_IMAGE}:${DOCKER_TAG} --format 'table {{.Size}}' | tail -n 1)"
echo ""
echo "🚀 L'image est maintenant prête pour le déploiement sur Hostinger!" 