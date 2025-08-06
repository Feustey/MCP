#!/bin/bash
# Script de build et push vers Docker Hub
# Usage: ./build-and-push-dockerhub.sh [tag]

set -e

# Configuration
DOCKER_USERNAME="feustey"
DOCKER_REPO="dazno"
DEFAULT_TAG="latest"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Vérification des prérequis
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé ou n'est pas dans le PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker n'est pas démarré ou vous n'avez pas les permissions"
    fi
}

# Connexion à Docker Hub
docker_login() {
    log "Connexion à Docker Hub..."
    if [ -z "$DOCKER_PASSWORD" ]; then
        warn "Variable DOCKER_PASSWORD non définie, connexion interactive requise"
        docker login
    else
        echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
    fi
}

# Build de l'image
build_image() {
    local tag=${1:-$DEFAULT_TAG}
    local image_name="${DOCKER_USERNAME}/${DOCKER_REPO}:${tag}"
    
    log "Build de l'image Docker: $image_name"
    log "Utilisation du Dockerfile.hub"
    
    # Build avec cache
    docker build \
        --file Dockerfile.hub \
        --tag "$image_name" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --cache-from "$image_name" \
        .
    
    log "Image buildée avec succès: $image_name"
    return 0
}

# Push vers Docker Hub
push_image() {
    local tag=${1:-$DEFAULT_TAG}
    local image_name="${DOCKER_USERNAME}/${DOCKER_REPO}:${tag}"
    
    log "Push de l'image vers Docker Hub: $image_name"
    docker push "$image_name"
    log "Image pushée avec succès!"
    
    # Tag également comme latest si ce n'est pas déjà le cas
    if [ "$tag" != "latest" ]; then
        log "Création du tag 'latest'..."
        docker tag "$image_name" "${DOCKER_USERNAME}/${DOCKER_REPO}:latest"
        docker push "${DOCKER_USERNAME}/${DOCKER_REPO}:latest"
        log "Tag 'latest' pushé!"
    fi
}

# Nettoyage des images locales (optionnel)
cleanup() {
    local tag=${1:-$DEFAULT_TAG}
    local image_name="${DOCKER_USERNAME}/${DOCKER_REPO}:${tag}"
    
    read -p "Voulez-vous nettoyer les images locales? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Nettoyage des images locales..."
        docker rmi "$image_name" || warn "Impossible de supprimer l'image locale"
        if [ "$tag" != "latest" ]; then
            docker rmi "${DOCKER_USERNAME}/${DOCKER_REPO}:latest" || warn "Impossible de supprimer l'image latest locale"
        fi
    fi
}

# Fonction principale
main() {
    local tag=${1:-$DEFAULT_TAG}
    
    log "=== Build et Push Docker Hub ==="
    log "Repository: ${DOCKER_USERNAME}/${DOCKER_REPO}"
    log "Tag: $tag"
    log "Dockerfile: Dockerfile.hub"
    echo
    
    # Vérifications
    check_docker
    
    # Connexion
    docker_login
    
    # Build
    build_image "$tag"
    
    # Push
    push_image "$tag"
    
    # Affichage des informations finales
    echo
    log "=== Succès! ==="
    log "Image disponible sur: https://hub.docker.com/r/${DOCKER_USERNAME}/${DOCKER_REPO}"
    log "Pour utiliser: docker pull ${DOCKER_USERNAME}/${DOCKER_REPO}:${tag}"
    echo
    
    # Nettoyage optionnel
    cleanup "$tag"
}

# Affichage de l'aide
show_help() {
    echo "Usage: $0 [OPTIONS] [TAG]"
    echo
    echo "Build et push d'une image Docker vers Docker Hub"
    echo
    echo "Arguments:"
    echo "  TAG            Tag de l'image (défaut: latest)"
    echo
    echo "Options:"
    echo "  -h, --help     Afficher cette aide"
    echo
    echo "Variables d'environnement:"
    echo "  DOCKER_PASSWORD    Mot de passe Docker Hub (optionnel)"
    echo
    echo "Exemples:"
    echo "  $0                 # Build et push avec tag 'latest'"
    echo "  $0 v1.0.0         # Build et push avec tag 'v1.0.0'"
    echo "  DOCKER_PASSWORD=xxx $0 prod    # Build et push avec authentification automatique"
}

# Gestion des arguments
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac