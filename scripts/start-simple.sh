#!/bin/bash
# Script de démarrage MCP simplifié (sans backup)
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
    
    if ! docker info >/dev/null 2>&1; then
        error "Docker n'est pas disponible"
    fi
    
    log "✓ Docker est prêt"
}

# Démarrage des services principaux
start_services() {
    log "Démarrage des services MCP (version simplifiée)..."
    
    # Arrêt des anciens services
    docker-compose -f docker-compose.prod.yml --env-file .env.production down 2>/dev/null || true
    
    # Démarrage uniquement des services principaux
    log "Démarrage des services principaux..."
    docker-compose -f docker-compose.prod.yml --env-file .env.production up -d \
        mcp-api mongodb redis prometheus grafana alertmanager qdrant
    
    log "✓ Services principaux démarrés"
}

# Test de santé
health_check() {
    log "Vérification de la santé des services..."
    
    sleep 20
    
    # Test de l'API
    local api_ready=false
    for i in {1..15}; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            api_ready=true
            break
        fi
        sleep 3
    done
    
    if $api_ready; then
        log "✓ API MCP disponible sur http://localhost:8000"
    else
        warn "✗ API MCP pas encore disponible (vérifiez les logs)"
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
    echo "⚠️ Note: Service de backup désactivé pour ce démarrage rapide"
    echo ""
}

# Menu principal
main() {
    log "🚀 Démarrage MCP Production (Mode Simplifié)"
    
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