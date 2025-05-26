#!/bin/bash
# Script de démarrage rapide MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"
}

# Vérification Docker
check_docker() {
    log "Vérification de Docker..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker info >/dev/null 2>&1; then
            log "✓ Docker est prêt"
            return 0
        else
            warn "Docker pas encore prêt (tentative $attempt/$max_attempts)..."
            sleep 2
            ((attempt++))
        fi
    done
    
    error "Docker n'est pas disponible après $max_attempts tentatives"
}

# Démarrage des services
start_services() {
    log "Démarrage des services MCP..."
    
    # Arrêt des anciens services
    docker-compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null || true
    
    # Construction et démarrage
    log "Construction des images..."
    docker-compose -f docker-compose.prod.yml --env-file .env.production build --no-cache
    
    log "Démarrage des conteneurs..."
    docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
    
    log "✓ Services démarrés"
}

# Test de santé
health_check() {
    log "Vérification de la santé des services..."
    
    sleep 15
    
    # Test de l'API
    local api_ready=false
    for i in {1..10}; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            api_ready=true
            break
        fi
        sleep 3
    done
    
    if $api_ready; then
        log "✓ API MCP disponible sur http://localhost:8000"
    else
        warn "✗ API MCP pas encore disponible"
    fi
    
    # Test Grafana
    if curl -sf http://localhost:3000 >/dev/null 2>&1; then
        log "✓ Grafana disponible sur http://localhost:3000"
    else
        warn "✗ Grafana pas encore disponible"
    fi
}

# Affichage des informations
show_info() {
    echo ""
    echo "🎉 MCP est maintenant en cours d'exécution !"
    echo ""
    echo "📊 Services disponibles :"
    echo "  • API MCP:       http://localhost:8000"
    echo "  • Documentation: http://localhost:8000/docs"
    echo "  • Health Check:  http://localhost:8000/health"
    echo "  • Grafana:       http://localhost:3000"
    echo "  • Prometheus:    http://localhost:9090"
    echo ""
    echo "🔐 Identifiants Grafana :"
    echo "  • Utilisateur: admin"
    echo "  • Mot de passe: (voir config/credentials-production.md)"
    echo ""
    echo "📋 Commandes utiles :"
    echo "  • Status:     docker-compose -f docker-compose.prod.yml ps"
    echo "  • Logs API:   docker logs -f mcp-api-prod"
    echo "  • Arrêt:      docker-compose -f docker-compose.prod.yml down"
    echo ""
}

# Menu principal
main() {
    log "🚀 Démarrage MCP Production"
    
    # Vérifier le fichier .env.production
    if [[ ! -f ".env.production" ]]; then
        error "Fichier .env.production manquant !"
    fi
    
    check_docker
    start_services
    health_check
    show_info
    
    log "✅ Démarrage terminé avec succès !"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 