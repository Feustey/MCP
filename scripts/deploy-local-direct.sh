#!/bin/bash
# Script de déploiement local direct MCP
# Dernière mise à jour: 20 juin 2025

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_IMAGE="mcp-api:latest"
CONTAINER_NAME="mcp-api-local"
PORT="8000"

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Vérification des prérequis
check_requirements() {
    log "Vérification des prérequis..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    log "Prérequis validés ✓"
}

# Création du fichier .env pour le déploiement local
create_env_file() {
    log "Création du fichier .env pour déploiement local..."
    
    cat > .env.local << EOF
# Configuration MCP pour déploiement local
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Base de données MongoDB (Hostinger)
MONGO_URL=mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true
MONGO_NAME=mcp

# Redis (Hostinger)
REDIS_HOST=d4s8888skckos8c80w4swgcw
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=20

# Configuration IA
AI_OPENAI_API_KEY=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
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuration Lightning
LIGHTNING_LND_HOST=localhost:10009
LIGHTNING_LND_REST_URL=https://127.0.0.1:8080
LIGHTNING_USE_INTERNAL_LNBITS=true
LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits

# Configuration LNBits (requise)
LNBITS_INKEY=your_lnbits_inkey_here
LNBITS_ADMIN_KEY=your_lnbits_admin_key_here
LNBITS_URL=https://localhost:5000

# Configuration sécurité
SECURITY_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY
SECURITY_CORS_ORIGINS=["*"]
SECURITY_ALLOWED_HOSTS=["*"]

# Configuration performance
PERF_RESPONSE_CACHE_TTL=3600
PERF_EMBEDDING_CACHE_TTL=86400
PERF_MAX_WORKERS=4

# Configuration logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_ENABLE_STRUCTLOG=true
LOG_ENABLE_FILE_LOGGING=true
LOG_LOG_FILE_PATH=logs/mcp.log

# Configuration heuristiques
HEURISTIC_CENTRALITY_WEIGHT=0.4
HEURISTIC_CAPACITY_WEIGHT=0.2
HEURISTIC_REPUTATION_WEIGHT=0.2
HEURISTIC_FEES_WEIGHT=0.1
HEURISTIC_UPTIME_WEIGHT=0.1
HEURISTIC_VECTOR_WEIGHT=0.7
EOF

    log "Fichier .env.local créé ✓"
}

# Arrêt des conteneurs existants
stop_existing_containers() {
    log "Arrêt des conteneurs existants..."
    
    if docker ps -q --filter "name=$CONTAINER_NAME" | grep -q .; then
        docker stop "$CONTAINER_NAME" || warn "Impossible d'arrêter le conteneur existant"
        docker rm "$CONTAINER_NAME" || warn "Impossible de supprimer le conteneur existant"
    fi
    
    log "Conteneurs existants arrêtés ✓"
}

# Construction de l'image Docker
build_docker_image() {
    log "Construction de l'image Docker..."
    
    cd "$PROJECT_DIR"
    
    # Construction avec le Dockerfile local optimisé
    docker build -f Dockerfile.local -t "$DOCKER_IMAGE" . || error "Échec de la construction Docker"
    
    log "Image Docker construite ✓"
}

# Démarrage du conteneur
start_container() {
    log "Démarrage du conteneur..."
    
    # Création des répertoires nécessaires
    mkdir -p logs data
    
    # Démarrage du conteneur
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        -p "$PORT:8000" \
        --env-file .env.local \
        -v "$PROJECT_DIR/logs:/app/logs" \
        -v "$PROJECT_DIR/data:/app/data" \
        -v "$PROJECT_DIR/rag:/app/rag" \
        "$DOCKER_IMAGE" || error "Échec du démarrage du conteneur"
    
    log "Conteneur démarré ✓"
}

# Vérification de la santé
health_check() {
    log "Vérification de la santé de l'application..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -s -f "http://localhost:$PORT/health" > /dev/null; then
            log "✓ Application en ligne"
            return 0
        fi
        
        log "⏳ Attente de l'application... (tentative $((attempt + 1))/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    error "Timeout: L'application n'est pas devenue disponible"
}

# Affichage des informations
show_info() {
    log "=== DÉPLOIEMENT LOCAL TERMINÉ ==="
    
    echo ""
    echo "🌐 Services disponibles:"
    echo "  - API MCP:     http://localhost:$PORT"
    echo "  - Health:      http://localhost:$PORT/health"
    echo "  - Docs:        http://localhost:$PORT/docs"
    echo ""
    echo "📊 Commandes utiles:"
    echo "  - Logs:        docker logs -f $CONTAINER_NAME"
    echo "  - Status:      docker ps | grep $CONTAINER_NAME"
    echo "  - Arrêt:       docker stop $CONTAINER_NAME"
    echo "  - Redémarrage: docker restart $CONTAINER_NAME"
    echo ""
    echo "📁 Répertoires:"
    echo "  - Logs:        $PROJECT_DIR/logs/"
    echo "  - Données:     $PROJECT_DIR/data/"
    echo "  - RAG:         $PROJECT_DIR/rag/"
    echo ""
}

# Test de l'API
test_api() {
    log "Test de l'API..."
    
    # Test de santé
    if curl -s "http://localhost:$PORT/health" | grep -q "ok"; then
        log "✓ Endpoint /health fonctionne"
    else
        warn "✗ Endpoint /health ne fonctionne pas"
    fi
    
    # Test de la documentation
    if curl -s "http://localhost:$PORT/docs" | grep -q "Swagger"; then
        log "✓ Documentation Swagger accessible"
    else
        warn "✗ Documentation Swagger non accessible"
    fi
}

# Menu principal
main() {
    log "🚀 Déploiement local direct MCP"
    
    check_requirements
    create_env_file
    stop_existing_containers
    build_docker_image
    start_container
    health_check
    test_api
    show_info
    
    log "✅ Déploiement local réussi!"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 