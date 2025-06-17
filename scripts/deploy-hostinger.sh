#!/bin/bash
# Script de déploiement pour Hostinger
# Auteur: MCP Team
# Version: 1.0.0
# Dernière mise à jour: 27 mai 2025

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/mcp-deploy.log"

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

# Vérification des variables d'environnement
check_env() {
    info "Vérification des variables d'environnement..."
    
    required_vars=(
        "HOSTINGER_API_TOKEN"
        "OPENAI_API_KEY"
        "HOSTINGER_DOMAIN"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Variable d'environnement manquante: $var"
            exit 1
        fi
    done
    
    success "Variables d'environnement vérifiées"
}

# Création du fichier .env
create_env_file() {
    info "Création du fichier .env..."
    
    cat > .env << EOF
# Configuration MCP Lightning Optimizer pour Hostinger
# Généré automatiquement le $(date '+%Y-%m-%d %H:%M:%S')

# Environment
ENVIRONMENT=production
PORT=8000
WORKERS=2
LOG_LEVEL=INFO
LOG_FORMAT=json

# APIs externes
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=gpt-4o-mini
SPARKSEER_API_KEY=${SPARKSEER_API_KEY:-}
SPARKSEER_BASE_URL=${SPARKSEER_BASE_URL:-https://api.sparkseer.space}

# LNBits Configuration
LNBITS_URL=${LNBITS_URL:-}
LNBITS_API_KEY=${LNBITS_API_KEY:-}

# Cache Redis
REDIS_URL=${REDIS_URL:-redis://localhost:6379}
CACHE_TTL=300
CACHE_NAMESPACE=mcp

# Sécurité
SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
CORS_ORIGINS=https://dazno.de,https://api.dazno.de,https://${HOSTINGER_DOMAIN}
ALLOWED_HOSTS=${HOSTINGER_DOMAIN},api.dazno.de

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30

# Base de données
MONGO_URL=${MONGO_URL:-mongodb://localhost:27017}
MONGO_DB=${MONGO_DB:-mcp_production}
EOF

    success "Fichier .env créé"
}

# Validation de la configuration
validate_config() {
    info "Validation de la configuration..."
    
    # Vérifier la configuration nixpacks.toml
    if [[ ! -f "nixpacks.toml" ]]; then
        error "Fichier nixpacks.toml manquant"
        exit 1
    fi
    
    # Vérifier les requirements
    if [[ ! -f "requirements.txt" ]]; then
        error "Fichier requirements.txt manquant"
        exit 1
    fi
    
    # Vérifier la structure de l'application
    required_files=(
        "app/main.py"
        "src/clients/openai_client.py"
        "src/clients/sparkseer_client.py"
        "src/utils/cache_manager.py"
        "app/models/mcp_schemas.py"
        "app/routes/intelligence.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Fichier manquant: $file"
            exit 1
        fi
    done
    
    success "Configuration validée"
}

# Déploiement sur Hostinger
deploy_to_hostinger() {
    info "Déploiement sur Hostinger..."
    
    # Vérifier que git est configuré
    if ! git config --get user.name > /dev/null || ! git config --get user.email > /dev/null; then
        error "Git n'est pas configuré. Veuillez configurer user.name et user.email"
        exit 1
    fi
    
    # Commit des changements
    git add .
    git commit -m "Déploiement sur Hostinger - $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Push vers Hostinger
    git push hostinger main
    
    success "Déploiement terminé"
}

# Fonction principale
main() {
    info "Démarrage du déploiement..."
    
    check_env
    create_env_file
    validate_config
    deploy_to_hostinger
    
    success "Déploiement réussi !"
}

# Exécution
main 