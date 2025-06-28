#!/bin/bash
# Script de déploiement automatisé pour MCP sur Hostinger avec ressources locales
# Dernière mise à jour: 27 mai 2025

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/home/feustey/backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/tmp/mcp_deploy.log"
COMPOSE_FILE="docker-compose.hostinger-production.yml"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

error_exit() {
    error "$1"
    exit 1
}

# Gestion des signaux pour un arrêt propre
cleanup() {
    warn "Signal reçu, nettoyage en cours..."
    if [[ -f "/tmp/mcp_deploy_in_progress" ]]; then
        warn "Déploiement interrompu, rollback en cours..."
        rollback_deployment
    fi
    rm -f "/tmp/mcp_deploy_in_progress"
    exit 1
}

trap cleanup SIGINT SIGTERM

# Fonction de validation de l'environnement
validate_environment() {
    info "=== Validation de l'environnement ==="
    
    # Vérifier que nous sommes sur le bon serveur
    if [[ $(hostname) != "srv782904" ]] && [[ $(hostname) != "147.79.101.32" ]]; then
        error_exit "Ce script doit être exécuté sur le serveur Hostinger"
    fi
    
    # Vérifier les permissions
    if [[ $EUID -eq 0 ]]; then
        error_exit "Ce script ne doit PAS être exécuté en tant que root"
    fi
    
    # Vérifier les variables d'environnement critiques
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        error_exit "Fichier .env.production manquant"
    fi
    
    # Charger et valider les variables d'environnement
    source "$PROJECT_ROOT/.env.production"
    
    required_vars=(
        "MONGO_ROOT_USER"
        "MONGO_ROOT_PASSWORD" 
        "REDIS_PASSWORD"
        "JWT_SECRET"
        "TELEGRAM_BOT_TOKEN"
        "TELEGRAM_CHAT_ID"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error_exit "Variable d'environnement manquante: $var"
        fi
    done
    
    # Vérifier Docker et Docker Compose
    if ! command -v docker &> /dev/null; then
        error_exit "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose n'est pas installé"
    fi
    
    # Vérifier l'espace disque disponible
    available_space_gb=$(df /home/feustey | awk 'NR==2 {print int($4/1024/1024)}')
    if [[ $available_space_gb -lt 5 ]]; then
        error_exit "Espace disque insuffisant: ${available_space_gb}GB disponible, 5GB requis"
    fi
    
    # Vérifier la mémoire disponible
    available_memory_gb=$(free -g | awk 'NR==2{print $7}')
    if [[ $available_memory_gb -lt 2 ]]; then
        error_exit "Mémoire insuffisante: ${available_memory_gb}GB disponible, 2GB requis"
    fi
    
    success "✓ Validation de l'environnement réussie"
}

# Fonction de sauvegarde avant déploiement
backup_current_deployment() {
    info "=== Sauvegarde du déploiement actuel ==="
    
    mkdir -p "$BACKUP_DIR"
    
    # Sauvegarde des configurations
    info "Sauvegarde des configurations..."
    cp -r "$PROJECT_ROOT/config" "$BACKUP_DIR/" 2>/dev/null || warn "Pas de configuration à sauvegarder"
    cp "$PROJECT_ROOT/.env.production" "$BACKUP_DIR/" 2>/dev/null || warn "Pas de .env.production à sauvegarder"
    
    # Sauvegarde de la base de données MongoDB
    if docker ps | grep -q mcp-mongodb-hostinger; then
        info "Sauvegarde de MongoDB..."
        docker exec mcp-mongodb-hostinger mongodump \
            --username "$MONGO_ROOT_USER" \
            --password "$MONGO_ROOT_PASSWORD" \
            --authenticationDatabase admin \
            --out "/backups/$(basename "$BACKUP_DIR")" \
            --gzip || warn "Échec de la sauvegarde MongoDB"
    fi
    
    # Sauvegarde des données Redis
    if docker ps | grep -q mcp-redis-hostinger; then
        info "Sauvegarde de Redis..."
        docker exec mcp-redis-hostinger redis-cli --rdb "/data/dump_$(date +%Y%m%d_%H%M%S).rdb" || warn "Échec de la sauvegarde Redis"
    fi
    
    # Sauvegarde des logs récents
    info "Sauvegarde des logs..."
    cp -r "$PROJECT_ROOT/logs" "$BACKUP_DIR/" 2>/dev/null || warn "Pas de logs à sauvegarder"
    
    # Sauvegarde des données RAG
    if [[ -d "$PROJECT_ROOT/rag/RAG_assets" ]]; then
        info "Sauvegarde des assets RAG..."
        tar -czf "$BACKUP_DIR/rag_assets.tar.gz" -C "$PROJECT_ROOT/rag" RAG_assets || warn "Échec de la sauvegarde RAG"
    fi
    
    success "✓ Sauvegarde terminée dans $BACKUP_DIR"
}

# Fonction de mise à jour du code
update_code() {
    info "=== Mise à jour du code source ==="
    
    cd "$PROJECT_ROOT"
    
    # Vérifier l'état du repository Git
    if [[ -d ".git" ]]; then
        # Sauvegarder les changements locaux
        if ! git diff-index --quiet HEAD --; then
            warn "Changements locaux détectés, création d'un stash..."
            git stash push -m "Pre-deployment stash $(date +%Y%m%d_%H%M%S)"
        fi
        
        # Mise à jour depuis le repository
        info "Mise à jour depuis le repository Git..."
        git fetch origin
        git reset --hard origin/main || git reset --hard origin/master || warn "Impossible de mettre à jour depuis Git"
    else
        warn "Pas de repository Git détecté, utilisation du code local"
    fi
    
    success "✓ Code source mis à jour"
}

# Fonction de préparation des répertoires
prepare_directories() {
    info "=== Préparation des répertoires ==="
    
    cd "$PROJECT_ROOT"
    
    # Création des répertoires nécessaires
    mkdir -p logs data rag backups config/nginx config/mongodb config/prometheus config/grafana/provisioning
    
    # Création du script d'initialisation MongoDB
    cat > config/mongodb/init-mongo.js << 'EOF'
// Script d'initialisation MongoDB pour MCP
db = db.getSiblingDB('mcp_prod');

// Création des collections principales
db.createCollection('nodes');
db.createCollection('channels');
db.createCollection('metrics');
db.createCollection('optimizations');
db.createCollection('reports');

// Création des index
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.metrics.createIndex({ "timestamp": 1 });
db.optimizations.createIndex({ "node_id": 1, "timestamp": 1 });
db.reports.createIndex({ "created_at": 1 });

print('Base de données MCP initialisée avec succès');
EOF
    
    success "✓ Répertoires préparés"
}

# Fonction d'arrêt des services existants
stop_existing_services() {
    info "=== Arrêt des services existants ==="
    
    cd "$PROJECT_ROOT"
    
    # Arrêt des conteneurs Docker existants
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    fi
    
    # Arrêt des autres conteneurs MCP
    docker stop $(docker ps -q --filter "name=mcp-") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=mcp-") 2>/dev/null || true
    
    # Nettoyage des volumes orphelins
    docker volume prune -f || true
    
    success "✓ Services existants arrêtés"
}

# Fonction de construction et démarrage des services
build_and_start_services() {
    info "=== Construction et démarrage des services ==="
    
    cd "$PROJECT_ROOT"
    
    # Construction de l'image MCP
    info "Construction de l'image MCP..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache mcp-api
    
    # Démarrage des services
    info "Démarrage des services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    success "✓ Services démarrés"
}

# Fonction de vérification de la santé des services
check_services_health() {
    info "=== Vérification de la santé des services ==="
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        info "Tentative $attempt/$max_attempts..."
        
        # Vérifier l'API principale
        if curl -f http://localhost/health &>/dev/null; then
            success "API principale accessible"
            break
        fi
        
        # Vérifier les conteneurs
        if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
            warn "Certains conteneurs ne sont pas démarrés"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        error "Timeout lors de la vérification de la santé des services"
        docker-compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
    
    success "✓ Tous les services sont en bonne santé"
}

# Fonction de rollback
rollback_deployment() {
    warn "=== Rollback du déploiement ==="
    
    cd "$PROJECT_ROOT"
    
    # Arrêt des nouveaux services
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
    
    # Restauration des sauvegardes si disponibles
    if [[ -d "$BACKUP_DIR" ]]; then
        warn "Restauration des sauvegardes..."
        # Logique de restauration à implémenter selon les besoins
    fi
    
    warn "Rollback terminé"
}

# Fonction d'envoi de notification
send_notification() {
    local message="$1"
    local status="$2"
    
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${message}" \
            -d "parse_mode=HTML" || true
    fi
}

# Fonction d'affichage des informations de déploiement
show_deployment_info() {
    info "=== Informations de déploiement ==="
    echo
    echo "🌐 API accessible sur: http://147.79.101.32"
    echo "📊 Documentation: http://147.79.101.32/docs"
    echo "🔍 Health check: http://147.79.101.32/health"
    echo "📈 Métriques: http://147.79.101.32/metrics"
    echo
    echo "📊 Monitoring:"
    echo "  - Prometheus: http://147.79.101.32:9090"
    echo "  - Grafana: http://147.79.101.32:3000 (admin/Kq_by8iZB4XJFvwc)"
    echo
    echo "📋 Commandes utiles:"
    echo "  - Logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  - Status: docker-compose -f $COMPOSE_FILE ps"
    echo "  - Redémarrage: docker-compose -f $COMPOSE_FILE restart"
    echo "  - Arrêt: docker-compose -f $COMPOSE_FILE down"
    echo
    echo "💾 Sauvegarde: $BACKUP_DIR"
    echo
}

# Fonction principale
main() {
    info "=== Déploiement MCP Production sur Hostinger ==="
    
    # Marquer le début du déploiement
    echo "1" > /tmp/mcp_deploy_in_progress
    
    validate_environment
    backup_current_deployment
    update_code
    prepare_directories
    stop_existing_services
    build_and_start_services
    check_services_health
    show_deployment_info
    
    # Nettoyer le marqueur de déploiement
    rm -f /tmp/mcp_deploy_in_progress
    
    # Envoyer notification de succès
    send_notification "✅ Déploiement MCP réussi sur Hostinger\n🌐 API: http://147.79.101.32\n📊 Docs: http://147.79.101.32/docs" "success"
    
    success "Déploiement terminé avec succès!"
}

# Exécution
main "$@" 