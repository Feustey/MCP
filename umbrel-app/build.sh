#!/bin/bash
# Script de build et push pour l'image Docker MCP (Umbrel)

set -euo pipefail
IFS=$'\n\t'

# Configuration
REGISTRY="ghcr.io"
PROJECT="mcp"
VERSION=$(git describe --tags --always --dirty)
IMAGE_NAME="${REGISTRY}/${PROJECT}:${VERSION}"
IMAGE_LATEST="${REGISTRY}/${PROJECT}:latest"

# Fonctions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

check_docker_auth() {
    if ! docker info >/dev/null 2>&1; then
        log "ERREUR: Docker n'est pas accessible ou vous n'êtes pas connecté"
        exit 1
    fi
}

build_image() {
    log "Construction de l'image Docker..."
    DOCKER_BUILDKIT=1 docker build \
        --build-arg VERSION="${VERSION}" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        -t "${IMAGE_NAME}" \
        -t "${IMAGE_LATEST}" \
        ..
}

optimize_image() {
    if command -v docker-slim &> /dev/null; then
        log "Optimisation de l'image avec docker-slim..."
        docker-slim build \
            --tag "${IMAGE_NAME}.slim" \
            --tag "${IMAGE_LATEST}.slim" \
            "${IMAGE_NAME}"
        IMAGE_NAME="${IMAGE_NAME}.slim"
        IMAGE_LATEST="${IMAGE_LATEST}.slim"
    else
        log "AVERTISSEMENT: docker-slim non trouvé, l'optimisation est ignorée"
    fi
}

push_images() {
    log "Push des images vers le registry..."
    docker push "${IMAGE_NAME}"
    docker push "${IMAGE_LATEST}"
}

show_image_info() {
    local size
    size=$(docker image inspect "${IMAGE_NAME}" --format='{{.Size}}')
    local size_mb=$((size/1024/1024))
    log "Taille de l'image : ${size_mb} Mo"

    local hash
    hash=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE_NAME}")
    log "Hash SHA : ${hash}"
}

# Exécution principale
main() {
    log "Début du processus de build pour MCP version ${VERSION}"
    
    check_docker_auth
    build_image
    optimize_image
    push_images
    show_image_info
    
    log "Build et push terminés avec succès"
}

main "$@" 