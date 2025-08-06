#!/bin/bash
# Script de déploiement MCP avec Docker Hub
# Usage: ./deploy-dockerhub.sh [environment]

set -e

# Configuration
COMPOSE_FILE="docker-compose.dockerhub.yml"
PROJECT_NAME="mcp-dockerhub"
DEFAULT_ENV="production"

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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    # Fichier de configuration
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Fichier $COMPOSE_FILE non trouvé"
    fi
    
    log "Prérequis OK"
}

# Création des répertoires nécessaires
create_directories() {
    log "Création des répertoires nécessaires..."
    
    mkdir -p logs/nginx
    mkdir -p data
    mkdir -p rag
    mkdir -p backups
    
    # Vérification des configs nécessaires
    if [ ! -d "config/nginx" ]; then
        warn "Répertoire config/nginx manquant"
    fi
    
    if [ ! -d "config/prometheus" ]; then
        warn "Répertoire config/prometheus manquant"
    fi
    
    if [ ! -d "config/grafana" ]; then
        warn "Répertoire config/grafana manquant"
    fi
    
    log "Répertoires créés"
}

# Pull des dernières images
pull_images() {
    log "Récupération des dernières images Docker Hub..."
    
    # Pull de l'image principale
    docker pull feustey/dazno:latest
    
    # Pull des autres images
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" pull
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" pull
    fi
    
    log "Images récupérées"
}

# Démarrage des services
start_services() {
    log "Démarrage des services..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    fi
    
    log "Services démarrés"
}

# Vérification de la santé des services
check_health() {
    log "Vérification de la santé des services..."
    
    # Attendre que les services démarrent
    sleep 30
    
    # Vérifier l'API MCP
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ API MCP opérationnelle"
    else
        warn "✗ API MCP non accessible"
    fi
    
    # Vérifier Nginx
    if curl -f http://localhost:80 > /dev/null 2>&1; then
        log "✓ Nginx opérationnel"
    else
        warn "✗ Nginx non accessible"
    fi
    
    # Vérifier Prometheus
    if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
        log "✓ Prometheus opérationnel"
    else
        warn "✗ Prometheus non accessible"
    fi
    
    # Vérifier Grafana
    if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
        log "✓ Grafana opérationnel"
    else
        warn "✗ Grafana non accessible"
    fi
    
    # Vérifier Qdrant
    if curl -f http://localhost:6333/ > /dev/null 2>&1; then
        log "✓ Qdrant opérationnel"
    else
        warn "✗ Qdrant non accessible"
    fi
}

# Affichage des informations de déploiement
show_deployment_info() {
    echo
    log "=== Déploiement terminé ==="
    echo
    info "Services disponibles :"
    info "  • API MCP:        http://localhost:8000"
    info "  • Documentation:  http://localhost:8000/docs"
    info "  • Nginx:          http://localhost:80"
    info "  • Prometheus:     http://localhost:9090"
    info "  • Grafana:        http://localhost:3000 (admin/admin123)"
    info "  • Qdrant:         http://localhost:6333"
    echo
    info "Commandes utiles :"
    info "  • Logs:           docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f"
    info "  • Status:         docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps"
    info "  • Stop:           docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down"
    info "  • Update:         ./scripts/deploy-dockerhub.sh"
    echo
}

# Arrêt des services
stop_services() {
    log "Arrêt des services..."
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    fi
    
    log "Services arrêtés"
}

# Fonction principale
main() {
    local env=${1:-$DEFAULT_ENV}
    
    log "=== Déploiement MCP via Docker Hub ==="
    log "Environnement: $env"
    log "Fichier compose: $COMPOSE_FILE"
    log "Projet: $PROJECT_NAME"
    echo
    
    # Vérifications
    check_prerequisites
    
    # Préparation
    create_directories
    
    # Déploiement
    pull_images
    start_services
    
    # Vérifications
    check_health
    
    # Informations
    show_deployment_info
}

# Fonction de mise à jour
update() {
    log "=== Mise à jour MCP ==="
    
    # Pull des nouvelles images
    pull_images
    
    # Redémarrage des services
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --force-recreate
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --force-recreate
    fi
    
    # Vérifications
    check_health
    
    log "Mise à jour terminée"
}

# Affichage de l'aide
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Déploiement MCP avec Docker Hub"
    echo
    echo "Commandes:"
    echo "  deploy         Déployer les services (défaut)"
    echo "  update         Mettre à jour les services"
    echo "  stop           Arrêter les services"
    echo "  status         Afficher le statut des services"
    echo "  logs           Afficher les logs"
    echo "  help           Afficher cette aide"
    echo
    echo "Options:"
    echo "  -h, --help     Afficher cette aide"
    echo
    echo "Exemples:"
    echo "  $0             # Déployer en production"
    echo "  $0 deploy      # Déployer explicitement"
    echo "  $0 update      # Mettre à jour"
    echo "  $0 stop        # Arrêter"
    echo "  $0 status      # Voir le statut"
}

# Affichage du statut
show_status() {
    log "Statut des services:"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    fi
}

# Affichage des logs
show_logs() {
    log "Logs des services (Ctrl+C pour quitter):"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
    else
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
    fi
}

# Gestion des arguments
case "$1" in
    deploy|"")
        main "$2"
        ;;
    update)
        update
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|-h|--help)
        show_help
        exit 0
        ;;
    *)
        error "Commande inconnue: $1. Utilisez '$0 help' pour voir les commandes disponibles."
        ;;
esac