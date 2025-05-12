#!/bin/bash
# Script de build et push pour l'image Docker Token4Good (Umbrel)

set -e

IMAGE_NAME="tonuser/token4good:latest"

# Build image
DOCKER_BUILDKIT=1 docker build -t $IMAGE_NAME ..

# Minification avec docker-slim (optionnel, nécessite docker-slim installé)
if command -v docker-slim &> /dev/null; then
  docker-slim build --tag $IMAGE_NAME.slim $IMAGE_NAME
  IMAGE_NAME="$IMAGE_NAME.slim"
fi

# Push image

docker push $IMAGE_NAME

# Affiche la taille de l'image
SIZE=$(docker image inspect $IMAGE_NAME --format='{{.Size}}')
SIZE_MB=$((SIZE/1024/1024))
echo "Taille de l'image : $SIZE_MB Mo"

# Affiche le hash SHA
HASH=$(docker inspect --format='{{index .RepoDigests 0}}' $IMAGE_NAME)
echo "Hash SHA : $HASH" 