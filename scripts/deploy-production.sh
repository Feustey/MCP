#!/bin/bash
# Script de déploiement MCP Production
# Dernière mise à jour: 7 mai 2025

set -e

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/opt/mcp/backups"
DATA_DIR="/opt/mcp/data"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Vérifications préalables
check_requirements() {
    log "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    # Vérifier le fichier .env.production
    if [[ ! -f "$PROJECT_DIR/.env.production" ]]; then
        error "Fichier .env.production manquant. Utilisez config/env.production.template"
    fi
    
    log "Prérequis validés ✓"
}

# Création des répertoires système
setup_directories() {
    log "Création des répertoires système..."
    
    sudo mkdir -p /opt/mcp/data/{mongodb,redis,prometheus,grafana,qdrant,alertmanager}
    sudo mkdir -p /opt/mcp/backups
    sudo mkdir -p /opt/mcp/logs
    
    # Permissions correctes
    sudo chown -R 1000:1000 /opt/mcp/data/
    sudo chown -R 1000:1000 /opt/mcp/backups/
    sudo chown -R 1000:1000 /opt/mcp/logs/
    
    log "Répertoires créés ✓"
}

# Sauvegarde avant déploiement
backup_before_deploy() {
    if [[ -f "$PROJECT_DIR/.env.production" ]] && docker-compose -f "$PROJECT_DIR/docker-compose.prod.yml" ps -q | grep -q .; then
        log "Sauvegarde avant déploiement..."
        
        # Créer une sauvegarde d'urgence
        BACKUP_NAME="pre_deploy_$(date +%Y%m%d_%H%M%S)"
        sudo mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
        
        # Copier les données importantes
        if [[ -d "/opt/mcp/data" ]]; then
            sudo cp -r /opt/mcp/data "$BACKUP_DIR/$BACKUP_NAME/" || warn "Impossible de sauvegarder les données"
        fi
        
        log "Sauvegarde pré-déploiement créée: $BACKUP_NAME ✓"
    fi
}

# Arrêt des services existants
stop_services() {
    log "Arrêt des services existants..."
    
    cd "$PROJECT_DIR"
    if docker-compose -f docker-compose.prod.yml ps -q | grep -q .; then
        docker-compose -f docker-compose.prod.yml down --remove-orphans
    fi
    
    log "Services arrêtés ✓"
}

# Construction et démarrage
deploy_services() {
    log "Déploiement des services..."
    
    cd "$PROJECT_DIR"
    
    # Construction des images
    log "Construction des images Docker..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Démarrage des services
    log "Démarrage des services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    log "Services déployés ✓"
}

# Vérification de la santé des services
health_check() {
    log "Vérification de la santé des services..."
    
    # Attendre que les services soient prêts
    sleep 30
    
    # Vérifier chaque service
    services=("mcp-api-prod" "mcp-mongodb-prod" "mcp-redis-prod" "mcp-prometheus-prod" "mcp-grafana-prod")
    
    for service in "${services[@]}"; do
        if docker ps --filter "name=$service" --filter "status=running" | grep -q "$service"; then
            log "✓ $service est en cours d'exécution"
        else
            error "✗ $service n'est pas en cours d'exécution"
        fi
    done
    
    # Test de l'endpoint de santé
    log "Test de l'API..."
    sleep 10
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ API MCP répond correctement"
    else
        warn "✗ API MCP ne répond pas encore (vérifiez les logs)"
    fi
    
    log "Vérifications de santé terminées"
}

# Affichage des informations de déploiement
show_deployment_info() {
    log "=== DÉPLOIEMENT TERMINÉ ==="
    
    echo ""
    echo "🌐 Services disponibles:"
    echo "  - API MCP:     http://localhost:8000"
    echo "  - Grafana:     http://localhost:3000"
    echo "  - Prometheus:  http://localhost:9090"
    echo ""
    echo "📊 Commandes utiles:"
    echo "  - Logs API:        docker logs -f mcp-api-prod"
    echo "  - Status:          docker-compose -f docker-compose.prod.yml ps"
    echo "  - Arrêt:           docker-compose -f docker-compose.prod.yml down"
    echo ""
    echo "📁 Répertoires:"
    echo "  - Données:         /opt/mcp/data/"
    echo "  - Sauvegardes:     /opt/mcp/backups/"
    echo "  - Logs:            /opt/mcp/logs/"
    echo ""
}

# Menu principal
main() {
    log "🚀 Déploiement MCP Production"
    
    check_requirements
    setup_directories
    backup_before_deploy
    stop_services
    deploy_services
    health_check
    show_deployment_info
    
    log "✅ Déploiement réussi!"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 