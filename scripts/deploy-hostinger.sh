#!/bin/bash
# Script de déploiement MCP sur Hostinger avec Nixpacks
# Version 1.0.0 - Optimisé pour production

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Configuration
PROJECT_NAME="mcp-lightning-optimizer"
HOSTINGER_DOMAIN=${HOSTINGER_DOMAIN:-"api.dazno.de"}
GIT_REPOSITORY=${GIT_REPOSITORY:-"https://github.com/Feustey/MCP.git"}
GIT_BRANCH=${GIT_BRANCH:-"berty"}

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
check_requirements() {
    log "🔍 Vérification des prérequis..."
    
    # Vérifier que git est installé
    if ! command -v git &> /dev/null; then
        error "Git n'est pas installé"
    fi
    
    # Vérifier que curl est installé
    if ! command -v curl &> /dev/null; then
        error "curl n'est pas installé"
    fi
    
    # Vérifier les variables d'environnement critiques
    required_vars=(
        "OPENAI_API_KEY"
        "HOSTINGER_API_TOKEN"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Variable d'environnement manquante: $var"
        fi
    done
    
    log "✅ Prérequis validés"
}

# Configuration des variables d'environnement pour Hostinger
setup_environment() {
    log "⚙️ Configuration de l'environnement..."
    
    # Créer le fichier .env pour Hostinger
    cat > .env.hostinger << EOF
# MCP Lightning Optimizer - Configuration Hostinger
ENVIRONMENT=production
PORT=8000
WORKERS=2

# APIs externes
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
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

    log "✅ Fichier d'environnement créé"
}

# Validation de la configuration
validate_config() {
    log "🔍 Validation de la configuration..."
    
    # Vérifier la configuration nixpacks.toml
    if [[ ! -f "nixpacks.toml" ]]; then
        error "Fichier nixpacks.toml manquant"
    fi
    
    # Vérifier les requirements
    if [[ ! -f "requirements.txt" ]]; then
        error "Fichier requirements.txt manquant"
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
        fi
    done
    
    log "✅ Configuration validée"
}

# Build local pour tester
build_locally() {
    log "🔨 Build local avec Nixpacks..."
    
    # Installer nixpacks si nécessaire
    if ! command -v nixpacks &> /dev/null; then
        info "Installation de Nixpacks..."
        curl -sSL https://nixpacks.com/install.sh | bash
        export PATH="$HOME/.nixpacks/bin:$PATH"
    fi
    
    # Build de l'image avec variables d'environnement
    source .env.hostinger
    nixpacks build . --name "$PROJECT_NAME" \
        --config nixpacks.toml \
        --env ENVIRONMENT="$ENVIRONMENT" \
        --env PORT="$PORT" \
        --env OPENAI_API_KEY="$OPENAI_API_KEY" \
        --env REDIS_URL="$REDIS_URL" \
        --env SECRET_KEY="$SECRET_KEY"
    
    log "✅ Build local réussi"
}

# Test de l'application localement
test_locally() {
    log "🧪 Tests locaux..."
    
    # Démarrer l'application en background
    info "Démarrage de l'application de test..."
    docker run -d --name "test-$PROJECT_NAME" \
        -p 8000:8000 \
        --env-file .env.hostinger \
        "$PROJECT_NAME" || error "Impossible de démarrer l'application"
    
    # Attendre que l'app soit prête
    sleep 10
    
    # Test de health check
    if curl -f http://localhost:8000/api/v1/health; then
        log "✅ Health check réussi"
    else
        error "Health check échoué"
    fi
    
    # Test de l'endpoint racine
    if curl -f http://localhost:8000/; then
        log "✅ Endpoint racine accessible"
    else
        warn "Endpoint racine non accessible"
    fi
    
    # Nettoyer
    docker stop "test-$PROJECT_NAME" || true
    docker rm "test-$PROJECT_NAME" || true
    
    log "✅ Tests locaux terminés"
}

# Déploiement sur Hostinger
deploy_to_hostinger() {
    log "🚀 Déploiement sur Hostinger..."
    
    # Préparation du payload de déploiement
    cat > deploy_payload.json << EOF
{
    "project_name": "$PROJECT_NAME",
    "repository": "$GIT_REPOSITORY",
    "branch": "$GIT_BRANCH",
    "build_config": {
        "nixpacks_config": "nixpacks.toml",
        "environment_file": ".env.hostinger"
    },
    "runtime_config": {
        "port": 8000,
        "health_check": "/api/v1/health",
        "scaling": {
            "min_instances": 1,
            "max_instances": 3
        }
    }
}
EOF

    # API call vers Hostinger
    if curl -X POST \
        -H "Authorization: Bearer $HOSTINGER_API_TOKEN" \
        -H "Content-Type: application/json" \
        -d @deploy_payload.json \
        "https://api.hostinger.com/v1/deployments"; then
        log "✅ Déploiement initié sur Hostinger"
    else
        error "Échec du déploiement sur Hostinger"
    fi
    
    # Nettoyage
    rm -f deploy_payload.json
}

# Vérification post-déploiement
verify_deployment() {
    log "🔍 Vérification du déploiement..."
    
    # Attendre que le déploiement soit prêt
    info "Attente de la propagation du déploiement (60s)..."
    sleep 60
    
    # Test de l'URL de production
    max_attempts=5
    attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        info "Tentative $attempt/$max_attempts..."
        
        if curl -f "https://$HOSTINGER_DOMAIN/api/v1/health"; then
            log "✅ Déploiement vérifié et opérationnel"
            return 0
        fi
        
        sleep 30
        ((attempt++))
    done
    
    warn "Impossible de vérifier le déploiement automatiquement"
    warn "Vérifiez manuellement: https://$HOSTINGER_DOMAIN/api/v1/health"
}

# Configuration des webhooks de monitoring
setup_monitoring() {
    log "📊 Configuration du monitoring..."
    
    # URL de webhook pour les alertes (ex: Discord, Slack)
    if [[ -n "${WEBHOOK_URL:-}" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🚀 MCP Lightning Optimizer déployé sur $HOSTINGER_DOMAIN\"}"
    fi
    
    log "✅ Monitoring configuré"
}

# Rollback en cas d'échec
rollback_deployment() {
    error "🔄 Rollback du déploiement..."
    
    # Logique de rollback via API Hostinger
    if [[ -n "${HOSTINGER_API_TOKEN:-}" ]]; then
        curl -X POST \
            -H "Authorization: Bearer $HOSTINGER_API_TOKEN" \
            "https://api.hostinger.com/v1/deployments/$PROJECT_NAME/rollback"
    fi
    
    error "Rollback effectué"
}

# Fonction principale
main() {
    log "🚀 Démarrage du déploiement MCP Lightning Optimizer"
    log "Target: $HOSTINGER_DOMAIN"
    log "Repository: $GIT_REPOSITORY"
    log "Branch: $GIT_BRANCH"
    
    # Trap pour rollback en cas d'erreur
    trap rollback_deployment ERR
    
    check_requirements
    setup_environment
    validate_config
    
    # Build et test local (optionnel en mode CI/CD)
    if [[ "${SKIP_LOCAL_TEST:-false}" != "true" ]]; then
        build_locally
        test_locally
    fi
    
    deploy_to_hostinger
    verify_deployment
    setup_monitoring
    
    log "🎉 Déploiement MCP Lightning Optimizer terminé avec succès!"
    log "🌐 URL: https://$HOSTINGER_DOMAIN"
    log "📚 Documentation: https://$HOSTINGER_DOMAIN/docs"
    log "💾 Health Check: https://$HOSTINGER_DOMAIN/api/v1/health"
    
    # Nettoyer les fichiers temporaires
    rm -f .env.hostinger
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 