#!/bin/bash
#
# Docker Entrypoint pour MCP API Production
# Gère l'initialisation et le démarrage de l'application
#
# Dernière mise à jour: 12 octobre 2025

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[ENTRYPOINT]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[ENTRYPOINT]${NC} $1"
}

log_error() {
    echo -e "${RED}[ENTRYPOINT]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ENTRYPOINT]${NC} $1"
}

log_info "Starting MCP API container..."
log_info "Environment: ${ENVIRONMENT:-production}"
log_info "Python: $(python --version)"
log_info "Working directory: $(pwd)"

# Vérifier que les variables essentielles sont définies
if [ -z "$MONGODB_URL" ] && [ -z "$REDIS_URL" ]; then
    log_warning "Database URLs not configured - running in degraded mode"
fi

# Créer les répertoires nécessaires
mkdir -p /app/logs /app/data

# Attendre que les services soient disponibles (optionnel)
if [ -n "$WAIT_FOR_SERVICES" ]; then
    log_info "Waiting for services..."
    
    # Attendre MongoDB si configuré
    if [ -n "$MONGODB_HOST" ]; then
        log_info "Waiting for MongoDB at $MONGODB_HOST..."
        timeout=30
        while ! nc -z "$MONGODB_HOST" "${MONGODB_PORT:-27017}" 2>/dev/null; do
            timeout=$((timeout - 1))
            if [ $timeout -le 0 ]; then
                log_error "MongoDB not available after 30 seconds"
                break
            fi
            sleep 1
        done
        [ $timeout -gt 0 ] && log_success "MongoDB is ready"
    fi
    
    # Attendre Redis si configuré
    if [ -n "$REDIS_HOST" ]; then
        log_info "Waiting for Redis at $REDIS_HOST..."
        timeout=30
        while ! nc -z "$REDIS_HOST" "${REDIS_PORT:-6379}" 2>/dev/null; do
            timeout=$((timeout - 1))
            if [ $timeout -le 0 ]; then
                log_error "Redis not available after 30 seconds"
                break
            fi
            sleep 1
        done
        [ $timeout -gt 0 ] && log_success "Redis is ready"
    fi
fi

# Définir PYTHONPATH
export PYTHONPATH=/app:/app/src:$PYTHONPATH

# Afficher la configuration
log_info "Configuration:"
log_info "  - Host: ${HOST:-0.0.0.0}"
log_info "  - Port: ${PORT:-8000}"
log_info "  - Workers: ${WORKERS:-2}"
log_info "  - Log Level: ${LOG_LEVEL:-INFO}"
log_info "  - DRY_RUN: ${DRY_RUN:-true}"

# Exécuter les migrations si nécessaire
if [ -n "$RUN_MIGRATIONS" ]; then
    log_info "Running database migrations..."
    # python scripts/migrate.py || log_warning "Migrations failed or not needed"
fi

# Afficher les informations de démarrage
log_success "✅ Initialization complete"
log_info "Starting application with: $@"
log_info ""

# Démarrer l'application
exec "$@"

