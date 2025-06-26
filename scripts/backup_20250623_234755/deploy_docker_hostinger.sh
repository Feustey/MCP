#!/bin/bash

# Script de déploiement Docker pour MCP sur Hostinger
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/mcp-docker-deploy.log"

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

# Vérification des prérequis
check_prerequisites() {
    info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Vérifier Git
    if ! command -v git &> /dev/null; then
        error "Git n'est pas installé"
        exit 1
    fi
    
    success "Prérequis vérifiés"
}

# Vérification des variables d'environnement
check_environment() {
    info "Vérification des variables d'environnement..."
    
    # Variables obligatoires
    required_vars=(
        "AI_OPENAI_API_KEY"
        "SECURITY_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            warn "Variable d'environnement manquante: $var"
            echo "Veuillez définir cette variable ou la configurer dans le fichier .env"
        fi
    done
    
    success "Variables d'environnement vérifiées"
}

# Création du fichier .env pour Docker
create_env_file() {
    info "Création du fichier .env pour Docker..."
    
    cat > .env.docker << EOF
# Configuration MCP pour Docker sur Hostinger
# Généré automatiquement le $(date '+%Y-%m-%d %H:%M:%S')

# Configuration de base
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
AI_OPENAI_API_KEY=${AI_OPENAI_API_KEY:-your_openai_key_here}
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuration Lightning
LIGHTNING_LND_HOST=localhost:10009
LIGHTNING_LND_REST_URL=https://127.0.0.1:8080
LIGHTNING_USE_INTERNAL_LNBITS=true
LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits

# Configuration sécurité
SECURITY_SECRET_KEY=${SECURITY_SECRET_KEY:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY}
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

# Configuration monitoring
GRAFANA_PASSWORD=admin123
EOF

    success "Fichier .env.docker créé"
}

# Validation de la configuration
validate_config() {
    info "Validation de la configuration..."
    
    # Vérifier les fichiers requis
    required_files=(
        "Dockerfile.hostinger"
        "docker-compose.hostinger.yml"
        "requirements-hostinger.txt"
        "src/api/main.py"
        "config.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Fichier manquant: $file"
            exit 1
        fi
    done
    
    success "Configuration validée"
}

# Construction de l'image Docker
build_docker_image() {
    info "Construction de l'image Docker..."
    
    # Arrêt des conteneurs existants
    docker-compose -f docker-compose.hostinger.yml down --remove-orphans || true
    
    # Construction de l'image
    docker-compose -f docker-compose.hostinger.yml build --no-cache
    
    if [[ $? -eq 0 ]]; then
        success "Image Docker construite avec succès"
    else
        error "Échec de la construction de l'image Docker"
        exit 1
    fi
}

# Démarrage des services
start_services() {
    info "Démarrage des services Docker..."
    
    # Démarrage avec le fichier .env.docker
    docker-compose -f docker-compose.hostinger.yml --env-file .env.docker up -d
    
    if [[ $? -eq 0 ]]; then
        success "Services démarrés avec succès"
    else
        error "Échec du démarrage des services"
        exit 1
    fi
}

# Vérification du déploiement
verify_deployment() {
    info "Vérification du déploiement..."
    
    # Attendre que les services démarrent
    sleep 10
    
    # Vérifier les conteneurs
    if docker-compose -f docker-compose.hostinger.yml ps | grep -q "Up"; then
        success "Conteneurs en cours d'exécution"
    else
        error "Conteneurs non démarrés"
        docker-compose -f docker-compose.hostinger.yml logs
        exit 1
    fi
    
    # Test de santé de l'API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "API accessible et fonctionnelle"
    else
        warn "API non accessible immédiatement, vérification des logs..."
        docker-compose -f docker-compose.hostinger.yml logs mcp-api
    fi
}

# Configuration Git pour déploiement
setup_git_deployment() {
    info "Configuration Git pour déploiement..."
    
    # Vérifier que git est configuré
    if ! git config --get user.name > /dev/null || ! git config --get user.email > /dev/null; then
        error "Git n'est pas configuré. Veuillez configurer user.name et user.email"
        exit 1
    fi
    
    # Ajouter les fichiers de déploiement
    git add docker-compose.hostinger.yml Dockerfile.hostinger scripts/start.sh .env.docker
    
    # Commit des changements
    git commit -m "feat: Déploiement Docker pour Hostinger - $(date '+%Y-%m-%d %H:%M:%S')" || {
        warn "Aucun changement à commiter"
    }
    
    success "Configuration Git terminée"
}

# Affichage des informations de déploiement
show_deployment_info() {
    info "Informations de déploiement:"
    echo ""
    echo "🌐 Services déployés:"
    echo "  - API MCP: http://localhost:8000"
    echo "  - Documentation: http://localhost:8000/docs"
    echo "  - Health check: http://localhost:8000/health"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000 (admin/admin123)"
    echo ""
    echo "📋 Commandes utiles:"
    echo "  - Voir les logs: docker-compose -f docker-compose.hostinger.yml logs -f"
    echo "  - Arrêter: docker-compose -f docker-compose.hostinger.yml down"
    echo "  - Redémarrer: docker-compose -f docker-compose.hostinger.yml restart"
    echo "  - Statut: docker-compose -f docker-compose.hostinger.yml ps"
    echo ""
    echo "🔧 Pour le déploiement sur Hostinger:"
    echo "  git push origin main"
    echo "  # Puis sur le serveur Hostinger:"
    echo "  docker-compose -f docker-compose.hostinger.yml --env-file .env.docker up -d"
}

# Fonction principale
main() {
    info "Démarrage du déploiement Docker pour Hostinger..."
    
    check_prerequisites
    check_environment
    create_env_file
    validate_config
    build_docker_image
    start_services
    verify_deployment
    setup_git_deployment
    show_deployment_info
    
    success "Déploiement Docker terminé avec succès !"
}

# Exécution
main "$@" 