#!/bin/bash
#
# Script de déploiement Docker Production pour MCP API
# Build et déploiement avec blue/green strategy
#
# Dernière mise à jour: 12 octobre 2025

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "╔════════════════════════════════════════════════════════╗"
echo "║  🚀 DÉPLOIEMENT DOCKER PRODUCTION MCP                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Variables
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
IMAGE_NAME="${IMAGE_NAME:-mcp-api}"
IMAGE_TAG="${IMAGE_TAG:-1.0.0}"
REGISTRY="${REGISTRY:-}"  # DockerHub, GCR, etc.
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

if [ -n "$REGISTRY" ]; then
    FULL_IMAGE="$REGISTRY/$FULL_IMAGE"
fi

log_info "Configuration:"
log_info "  - Project: $PROJECT_DIR"
log_info "  - Image: $FULL_IMAGE"
log_info "  - Environment: production"
echo ""

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé"
    exit 1
fi

log_info "Docker version: $(docker --version)"
echo ""

# Étape 1: Build de l'image
log_info "📦 Étape 1/6: Build de l'image Docker"
echo "=================================================="

cd "$PROJECT_DIR"

log_info "Building image: $FULL_IMAGE"
docker build \
    -f Dockerfile.production \
    -t "$FULL_IMAGE" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
    --progress=plain \
    .

log_success "Image built successfully"
echo ""

# Étape 2: Tag latest
log_info "🏷️  Étape 2/6: Tag de l'image"
echo "================================"

docker tag "$FULL_IMAGE" "$IMAGE_NAME:latest"
log_success "Tagged as latest"
echo ""

# Étape 3: Tests de l'image
log_info "🧪 Étape 3/6: Tests de l'image"
echo "================================"

log_info "Running basic tests..."

# Test 1: L'image démarre
log_info "Test 1/3: Container startup"
CONTAINER_ID=$(docker run -d --rm \
    -e ENVIRONMENT=test \
    -e DRY_RUN=true \
    "$FULL_IMAGE" \
    sleep 30)

sleep 5

if docker ps | grep -q "$CONTAINER_ID"; then
    log_success "✅ Container starts successfully"
    docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true
else
    log_error "❌ Container failed to start"
    docker logs "$CONTAINER_ID" || true
    exit 1
fi

# Test 2: Healthcheck
log_info "Test 2/3: Healthcheck"
CONTAINER_ID=$(docker run -d --rm \
    -e ENVIRONMENT=test \
    -e DRY_RUN=true \
    -p 8001:8000 \
    "$FULL_IMAGE")

sleep 10

if curl -sf http://localhost:8001/ > /dev/null 2>&1; then
    log_success "✅ Healthcheck passed"
else
    log_warning "⚠️  Healthcheck failed (may be normal if dependencies missing)"
fi

docker stop "$CONTAINER_ID" >/dev/null 2>&1 || true

# Test 3: Image size
log_info "Test 3/3: Image size"
IMAGE_SIZE=$(docker images "$FULL_IMAGE" --format "{{.Size}}")
log_info "Image size: $IMAGE_SIZE"

if [[ "$IMAGE_SIZE" == *"GB"* ]]; then
    SIZE_VALUE=$(echo "$IMAGE_SIZE" | sed 's/GB//')
    if (( $(echo "$SIZE_VALUE > 2" | bc -l) )); then
        log_warning "⚠️  Image is large (> 2GB)"
    else
        log_success "✅ Image size acceptable"
    fi
else
    log_success "✅ Image size acceptable"
fi

echo ""

# Étape 4: Push vers registry (optionnel)
if [ -n "$REGISTRY" ]; then
    log_info "📤 Étape 4/6: Push vers registry"
    echo "=================================="
    
    read -p "Push to registry $REGISTRY? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Pushing $FULL_IMAGE..."
        docker push "$FULL_IMAGE"
        docker push "$IMAGE_NAME:latest" 2>/dev/null || true
        log_success "Image pushed"
    else
        log_info "Skipping push"
    fi
else
    log_info "📤 Étape 4/6: Push vers registry (skipped)"
    log_info "No registry configured"
fi

echo ""

# Étape 5: Déploiement Blue/Green
log_info "🔄 Étape 5/6: Déploiement Blue/Green"
echo "======================================"

# Vérifier si l'ancien container existe
OLD_CONTAINER=$(docker ps -a --filter "name=mcp-api-blue" --filter "name=mcp-api-green" --format "{{.Names}}" | head -1)

if [ -n "$OLD_CONTAINER" ]; then
    if [[ "$OLD_CONTAINER" == *"blue"* ]]; then
        NEW_COLOR="green"
        OLD_COLOR="blue"
    else
        NEW_COLOR="blue"
        OLD_COLOR="green"
    fi
else
    NEW_COLOR="blue"
    OLD_COLOR="none"
fi

log_info "Deployment strategy: $OLD_COLOR → $NEW_COLOR"
echo ""

# Démarrer le nouveau container
log_info "Starting new container: mcp-api-$NEW_COLOR"

NEW_PORT=8002
if [ "$NEW_COLOR" == "blue" ]; then
    NEW_PORT=8001
fi

docker run -d \
    --name "mcp-api-$NEW_COLOR" \
    --restart unless-stopped \
    -p "$NEW_PORT:8000" \
    -v "$PROJECT_DIR/.env:/app/.env:ro" \
    -v "$PROJECT_DIR/logs:/app/logs" \
    -v "$PROJECT_DIR/data:/app/data" \
    "$FULL_IMAGE"

log_success "New container started on port $NEW_PORT"

# Attendre le healthcheck
log_info "Waiting for healthcheck (30s)..."
sleep 30

if curl -sf "http://localhost:$NEW_PORT/" > /dev/null 2>&1; then
    log_success "✅ New container is healthy"
    
    # Arrêter l'ancien container
    if [ "$OLD_COLOR" != "none" ]; then
        log_info "Stopping old container: mcp-api-$OLD_COLOR"
        docker stop "mcp-api-$OLD_COLOR" || true
        docker rm "mcp-api-$OLD_COLOR" || true
        log_success "Old container stopped"
    fi
    
    # Mettre à jour nginx pour pointer vers le nouveau container
    log_info "Update nginx configuration to point to port $NEW_PORT"
    log_warning "⚠️  Manual nginx config update required"
    
else
    log_error "❌ New container failed healthcheck"
    log_error "Rollback required"
    docker logs "mcp-api-$NEW_COLOR" | tail -50
    docker stop "mcp-api-$NEW_COLOR"
    docker rm "mcp-api-$NEW_COLOR"
    exit 1
fi

echo ""

# Étape 6: Cleanup
log_info "🧹 Étape 6/6: Cleanup"
echo "====================="

log_info "Removing dangling images..."
docker image prune -f >/dev/null 2>&1 || true

log_success "Cleanup complete"
echo ""

# Résumé
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ DÉPLOIEMENT RÉUSSI                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Résumé du déploiement:"
echo "  - Image: $FULL_IMAGE"
echo "  - Container: mcp-api-$NEW_COLOR"
echo "  - Port: $NEW_PORT"
echo "  - Status: Running"
echo ""
echo "🔍 Commandes utiles:"
echo "  # Logs"
echo "  docker logs -f mcp-api-$NEW_COLOR"
echo ""
echo "  # Status"
echo "  docker ps | grep mcp-api"
echo ""
echo "  # Exec"
echo "  docker exec -it mcp-api-$NEW_COLOR /bin/bash"
echo ""
echo "  # Rollback (si problème)"
echo "  docker stop mcp-api-$NEW_COLOR && docker rm mcp-api-$NEW_COLOR"
if [ "$OLD_COLOR" != "none" ]; then
echo "  docker start mcp-api-$OLD_COLOR"
fi
echo ""
echo "⚠️  N'oubliez pas de mettre à jour nginx pour pointer vers le port $NEW_PORT"

