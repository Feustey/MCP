#!/bin/bash
# Script de construction et push des images Docker
# À exécuter localement avec Docker installé

set -e

# Configuration
DOCKER_IMAGE="feustey/dazno"
BUILD_TAG=$(date +%Y%m%d-%H%M)
DOCKERFILE="Dockerfile.production"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Vérifications
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker n'est pas démarré"
    fi
    
    log "✅ Docker opérationnel"
}

# Construction
build_images() {
    log "🔨 Construction des images Docker..."
    
    # Nettoyer
    docker system prune -f --filter "until=24h" || true
    
    # Construire l'image principale
    log "Construction de $DOCKER_IMAGE:$BUILD_TAG"
    docker build -f $DOCKERFILE -t $DOCKER_IMAGE:$BUILD_TAG -t $DOCKER_IMAGE:latest .
    
    log "✅ Images construites"
    docker images | grep $DOCKER_IMAGE
}

# Push vers Docker Hub
push_images() {
    log "📤 Push vers Docker Hub..."
    
    # Vérifier la connexion
    if ! docker info | grep -q "Username"; then
        warn "Connexion à Docker Hub requise"
        docker login
    fi
    
    # Push des images
    docker push $DOCKER_IMAGE:$BUILD_TAG
    docker push $DOCKER_IMAGE:latest
    
    log "✅ Images poussées vers Docker Hub"
}

# Test de l'image
test_image() {
    log "🧪 Test de l'image construite..."
    
    # Test de démarrage
    CONTAINER_ID=$(docker run -d -p 8001:8000 $DOCKER_IMAGE:latest)
    
    # Attendre le démarrage
    sleep 10
    
    # Test du health check
    if curl -f http://localhost:8001/health &> /dev/null; then
        log "✅ Image fonctionnelle"
    else
        warn "⚠️  Health check échoué"
    fi
    
    # Nettoyer
    docker stop $CONTAINER_ID && docker rm $CONTAINER_ID
}

main() {
    log "🚀 Construction et push MCP Daznode"
    log "Tag de build: $BUILD_TAG"
    
    check_docker
    build_images
    
    # Test optionnel
    read -p "Tester l'image localement ? (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[OoYy]$ ]]; then
        test_image
    fi
    
    push_images
    
    log "🎉 Build et push terminés!"
    log "Images disponibles:"
    log "  - $DOCKER_IMAGE:$BUILD_TAG"
    log "  - $DOCKER_IMAGE:latest"
}

main "$@"