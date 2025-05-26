#!/bin/bash
# Script de déploiement simplifié pour MCP (sans Docker)
# Dernière mise à jour: 27 mai 2025

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/mcp_logs/deploy-simple.log"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Fonction principale
main() {
    info "=== PRÉPARATION DU DÉPLOIEMENT MCP ==="
    info "Mode: Préparation des configurations"
    info "Répertoire: $PROJECT_ROOT"
    
    # Créer le répertoire de logs
    mkdir -p "/tmp/mcp_logs"
    
    # Vérifier les fichiers de configuration
    info "=== Vérification des configurations ==="
    
    if [[ ! -f "$PROJECT_ROOT/.env.production" ]]; then
        error "Fichier .env.production manquant"
        exit 1
    fi
    
    # Charger les variables d'environnement
    source "$PROJECT_ROOT/.env.production"
    
    # Vérifier les variables critiques
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
            error "Variable d'environnement manquante: $var"
            exit 1
        fi
    done
    
    success "✓ Variables d'environnement validées"
    
    # Vérifier les fichiers de configuration Docker
    info "=== Vérification des fichiers Docker ==="
    
    required_files=(
        "docker-compose.prod.yml"
        "Dockerfile.prod"
        "config/mongodb/mongod.conf"
        "config/redis/redis-prod.conf"
        "config/prometheus/prometheus-prod.yml"
        "config/grafana/provisioning/datasources/prometheus.yml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            error "Fichier manquant: $file"
            exit 1
        fi
    done
    
    success "✓ Fichiers de configuration Docker présents"
    
    # Préparer les configurations
    info "=== Préparation des configurations ==="
    
    # Exécuter le script de préparation
    if [[ -f "$PROJECT_ROOT/scripts/prepare-config.sh" ]]; then
        "$PROJECT_ROOT/scripts/prepare-config.sh"
        success "✓ Configurations préparées"
    else
        warn "Script de préparation non trouvé"
    fi
    
    # Créer les répertoires nécessaires
    info "=== Création des répertoires ==="
    
    mkdir -p "$PROJECT_ROOT"/{logs,data,backups}
    mkdir -p "$PROJECT_ROOT/rag/RAG_assets"/{logs,reports,metrics}
    mkdir -p "/tmp/mcp_data"/{mongodb,redis,prometheus,grafana}
    
    success "✓ Répertoires créés"
    
    # Vérifier la structure du projet
    info "=== Vérification de la structure du projet ==="
    
    key_dirs=(
        "app"
        "src"
        "config"
        "rag"
        "scripts"
        "docs"
    )
    
    for dir in "${key_dirs[@]}"; do
        if [[ ! -d "$PROJECT_ROOT/$dir" ]]; then
            warn "Répertoire manquant: $dir"
        else
            success "✓ Répertoire présent: $dir"
        fi
    done
    
    # Résumé final
    info "=== RÉSUMÉ DE LA PRÉPARATION ==="
    success "✓ Configuration de production validée"
    success "✓ Fichiers Docker présents et configurés"
    success "✓ Variables d'environnement chargées"
    success "✓ Répertoires de données créés"
    
    info "Le système est prêt pour le déploiement Docker"
    info "Pour déployer avec Docker, utilisez: ./scripts/deploy.sh --dev"
    
    # Afficher les prochaines étapes
    info "=== PROCHAINES ÉTAPES ==="
    info "1. Démarrer Docker Desktop"
    info "2. Exécuter: docker-compose -f docker-compose.prod.yml up -d"
    info "3. Vérifier les services: docker-compose -f docker-compose.prod.yml ps"
    info "4. Tester l'API: curl http://localhost:8000/health"
    
    success "=== PRÉPARATION TERMINÉE AVEC SUCCÈS ==="
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 