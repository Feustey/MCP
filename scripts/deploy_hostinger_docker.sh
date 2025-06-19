#!/bin/bash

# Script de déploiement Docker sur serveur Hostinger
# À exécuter directement sur le serveur Hostinger
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
APP_DIR="/home/feustey"
BACKUP_DIR="/home/feustey/backups"
LOG_FILE="/var/log/mcp-docker-deploy.log"

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

# Vérification des prérequis sur le serveur
check_server_prerequisites() {
    info "Vérification des prérequis sur le serveur..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        info "Installation de Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        usermod -aG docker $USER
        rm get-docker.sh
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        info "Installation de Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    # Vérifier Git
    if ! command -v git &> /dev/null; then
        info "Installation de Git..."
        apt-get update && apt-get install -y git
    fi
    
    success "Prérequis vérifiés et installés"
}

# Sauvegarde de l'ancienne installation
backup_old_installation() {
    info "Sauvegarde de l'ancienne installation..."
    
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$APP_DIR" ] && [ -d "$APP_DIR/.git" ]; then
        local backup_name="backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$BACKUP_DIR/$backup_name" -C "$APP_DIR" .
        success "Sauvegarde créée: $backup_name"
    else
        warn "Aucune installation précédente à sauvegarder"
    fi
}

# Mise à jour du code depuis Git
update_code_from_git() {
    info "Mise à jour du code depuis Git..."
    
    if [ -d "$APP_DIR/.git" ]; then
        # Mise à jour du dépôt existant
        cd "$APP_DIR"
        git fetch origin
        git reset --hard origin/berty
        success "Code mis à jour depuis la branche berty"
    else
        # Clonage du dépôt
        if [ -d "$APP_DIR" ]; then
            rm -rf "$APP_DIR"
        fi
        git clone -b berty https://github.com/Feustey/MCP.git "$APP_DIR"
        success "Dépôt cloné depuis la branche berty"
    fi
}

# Configuration des variables d'environnement
setup_environment() {
    info "Configuration des variables d'environnement..."
    
    cd "$APP_DIR"
    
    # Création du fichier .env pour Docker avec les vraies valeurs
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

# Configuration IA (vraies valeurs)
AI_OPENAI_API_KEY=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
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuration Lightning
LIGHTNING_LND_HOST=localhost:10009
LIGHTNING_LND_REST_URL=https://127.0.0.1:8080
LIGHTNING_USE_INTERNAL_LNBITS=true
LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits

# Configuration sécurité (vraie clé)
SECURITY_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY
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

    success "Variables d'environnement configurées"
}

# Arrêt des services existants
stop_existing_services() {
    info "Arrêt des services existants..."
    
    cd "$APP_DIR"
    
    # Arrêt des conteneurs Docker
    if [ -f "docker-compose.hostinger.yml" ]; then
        docker-compose -f docker-compose.hostinger.yml down --remove-orphans || true
    fi
    
    # Arrêt des processus Python existants
    pkill -f "uvicorn.*app" || true
    pkill -f "python.*main" || true
    
    success "Services existants arrêtés"
}

# Construction et démarrage des services Docker
deploy_docker_services() {
    info "Déploiement des services Docker..."
    
    cd "$APP_DIR"
    
    # Construction de l'image
    info "Construction de l'image Docker..."
    docker-compose -f docker-compose.hostinger.yml build --no-cache
    
    # Démarrage des services
    info "Démarrage des services..."
    docker-compose -f docker-compose.hostinger.yml --env-file .env.docker up -d
    
    success "Services Docker déployés"
}

# Vérification du déploiement
verify_deployment() {
    info "Vérification du déploiement..."
    
    cd "$APP_DIR"
    
    # Attendre que les services démarrent
    sleep 15
    
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

# Configuration du reverse proxy Caddy
setup_caddy_proxy() {
    info "Configuration du reverse proxy Caddy..."
    
    # Vérifier si Caddy est installé
    if ! command -v caddy &> /dev/null; then
        info "Installation de Caddy..."
        apt-get update && apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
        apt-get update && apt-get install -y caddy
    fi
    
    # Configuration Caddy pour api.dazno.de
    cat > /etc/caddy/Caddyfile << 'EOF'
api.dazno.de {
    # Redirection HTTP vers HTTPS
    redir https://{host}{uri} permanent

    # Configuration SSL
    tls {
        protocols tls1.2 tls1.3
    }

    # Headers de sécurité
    header {
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # CORS
    header /api/* {
        Access-Control-Allow-Origin "https://app.dazno.de"
        Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
        Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With, X-API-Key"
        Access-Control-Allow-Credentials "true"
        Access-Control-Max-Age "3600"
    }

    # Rate limiting
    rate_limit {
        zone api {
            rate 10r/s
            burst 50
        }
    }

    # Reverse proxy vers l'application Docker
    reverse_proxy localhost:8000 {
        health_uri /health
        health_interval 30s
        health_timeout 10s
        health_status 200
    }
}
EOF

    # Redémarrage de Caddy
    systemctl restart caddy
    systemctl enable caddy
    
    success "Caddy configuré et démarré"
}

# Affichage des informations finales
show_final_info() {
    info "Déploiement terminé avec succès !"
    echo ""
    echo "🌐 Services accessibles:"
    echo "  - API MCP: https://api.dazno.de"
    echo "  - Documentation: https://api.dazno.de/docs"
    echo "  - Health check: https://api.dazno.de/health"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000 (admin/admin123)"
    echo ""
    echo "📋 Commandes utiles:"
    echo "  - Voir les logs: docker-compose -f docker-compose.hostinger.yml logs -f"
    echo "  - Arrêter: docker-compose -f docker-compose.hostinger.yml down"
    echo "  - Redémarrer: docker-compose -f docker-compose.hostinger.yml restart"
    echo "  - Statut: docker-compose -f docker-compose.hostinger.yml ps"
    echo "  - Logs Caddy: journalctl -u caddy -f"
    echo ""
    echo "🔧 Monitoring:"
    echo "  - Vérifier l'API: curl https://api.dazno.de/health"
    echo "  - Vérifier les conteneurs: docker ps"
    echo "  - Vérifier Caddy: systemctl status caddy"
}

# Fonction principale
main() {
    info "Démarrage du déploiement Docker sur Hostinger..."
    
    check_server_prerequisites
    backup_old_installation
    update_code_from_git
    setup_environment
    stop_existing_services
    deploy_docker_services
    verify_deployment
    setup_caddy_proxy
    show_final_info
    
    success "Déploiement Docker sur Hostinger terminé avec succès !"
}

# Exécution
main "$@" 