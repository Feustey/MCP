#!/bin/bash
# Script de déploiement unifié pour MCP sur Hostinger
# Dernière mise à jour: 27 mai 2025

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/home/feustey/backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/tmp/mcp_deploy_$(date +%Y%m%d_%H%M%S).log"
DOMAIN="api.dazno.de"

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
    exit 1
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Fonction de validation de l'environnement
validate_environment() {
    info "=== Validation de l'environnement ==="
    
    # Vérifier que nous sommes sur le bon serveur
    if [[ $(hostname) != "srv782904" ]] && [[ $(hostname) != "147.79.101.32" ]]; then
        error "Ce script doit être exécuté sur le serveur Hostinger"
    fi
    
    # Vérifier les permissions
    if [[ $EUID -eq 0 ]]; then
        error "Ce script ne doit PAS être exécuté en tant que root"
    fi
    
    # Vérifier Docker et Docker Compose
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    # Vérifier l'espace disque disponible
    available_space_gb=$(df /home/feustey | awk 'NR==2 {print int($4/1024/1024)}')
    if [[ $available_space_gb -lt 5 ]]; then
        error "Espace disque insuffisant: ${available_space_gb}GB disponible, 5GB requis"
    fi
    
    success "✓ Validation de l'environnement réussie"
}

# Fonction de sauvegarde
backup_current() {
    info "=== Sauvegarde de l'installation actuelle ==="
    
    mkdir -p "$BACKUP_DIR"
    
    # Sauvegarde des configurations
    if [[ -d "$PROJECT_ROOT/config" ]]; then
        cp -r "$PROJECT_ROOT/config" "$BACKUP_DIR/"
    fi
    
    if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
        cp "$PROJECT_ROOT/.env.production" "$BACKUP_DIR/"
    fi
    
    # Sauvegarde MongoDB si en cours d'exécution
    if docker ps | grep -q "mcp-mongodb"; then
        docker exec mcp-mongodb mongodump --out "/data/db/backup_$(date +%Y%m%d_%H%M%S)"
    fi
    
    success "✓ Sauvegarde terminée dans $BACKUP_DIR"
}

# Fonction d'arrêt des services existants
stop_services() {
    info "=== Arrêt des services existants ==="
    
    cd "$PROJECT_ROOT"
    
    # Arrêt des conteneurs Docker
    docker-compose -f docker-compose.yml down --remove-orphans || true
    docker-compose -f docker-compose.hostinger-production.yml down --remove-orphans || true
    
    # Nettoyage des conteneurs et volumes orphelins
    docker system prune -f
    docker volume prune -f
    
    success "✓ Services arrêtés et nettoyés"
}

# Fonction de préparation des répertoires
prepare_directories() {
    info "=== Préparation des répertoires ==="
    
    mkdir -p "$PROJECT_ROOT"/{logs,data,rag,config/{nginx,mongodb,redis,prometheus,grafana/provisioning}}
    
    success "✓ Répertoires préparés"
}

# Fonction de configuration de Nginx
configure_nginx() {
    info "=== Configuration de Nginx ==="
    
    # Configuration Nginx de base sans SSL
    cat > "$PROJECT_ROOT/config/nginx/nginx.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;
    
    # Upstream pour FastAPI
    upstream fastapi {
        server mcp-api:8000;
    }
    
    server {
        listen 80;
        server_name api.dazno.de;
        
        location / {
            proxy_pass http://fastapi;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /health {
            proxy_pass http://fastapi/health;
            access_log off;
        }
        
        location /docs {
            proxy_pass http://fastapi/docs;
        }
        
        location /metrics {
            proxy_pass http://fastapi/metrics;
            access_log off;
        }
    }
}
EOF
    
    success "✓ Configuration Nginx créée"
}

# Fonction de configuration de l'environnement
configure_env() {
    info "=== Configuration de l'environnement ==="
    
    cat > "$PROJECT_ROOT/.env.production" << 'EOF'
# Configuration MCP Production
# Généré le $(date '+%Y-%m-%d %H:%M:%S')

# Configuration de base
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true
LOG_LEVEL=INFO

# Configuration serveur
HOST=0.0.0.0
PORT=8000
WORKERS=4

# MongoDB
MONGO_URL=mongodb://mcp_admin:${MONGO_PASSWORD}@mongodb:27017/mcp_prod?authSource=admin
MONGO_NAME=mcp_prod

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_SSL=false
REDIS_MAX_CONNECTIONS=20

# Sécurité
JWT_SECRET=${JWT_SECRET}
SECURITY_CORS_ORIGINS=["https://app.dazno.de"]
SECURITY_ALLOWED_HOSTS=["api.dazno.de", "localhost"]

# Performance
PERF_RESPONSE_CACHE_TTL=3600
PERF_EMBEDDING_CACHE_TTL=86400
PERF_MAX_WORKERS=4

# Logging
LOG_FORMAT=json
LOG_ENABLE_STRUCTLOG=true
LOG_ENABLE_FILE_LOGGING=true
LOG_LOG_FILE_PATH=logs/mcp.log
EOF
    
    success "✓ Fichier .env.production créé"
}

# Fonction de déploiement Docker
deploy_docker() {
    info "=== Déploiement Docker ==="
    
    cd "$PROJECT_ROOT"
    
    # Construction et démarrage des services
    docker-compose -f docker-compose.hostinger-production.yml build --no-cache
    docker-compose -f docker-compose.hostinger-production.yml up -d
    
    success "✓ Services Docker déployés"
}

# Fonction de vérification de la santé
check_health() {
    info "=== Vérification de la santé des services ==="
    
    local max_attempts=30
    local attempt=1
    local health_url="http://localhost/health"
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$health_url" > /dev/null; then
            success "✓ API accessible et en bonne santé"
            return 0
        fi
        
        info "Tentative $attempt/$max_attempts..."
        sleep 10
        ((attempt++))
    done
    
    error "L'API n'est pas accessible après $max_attempts tentatives"
}

# Fonction de configuration SSL
configure_ssl() {
    info "=== Configuration SSL avec Let's Encrypt ==="
    
    # Installation de Certbot si nécessaire
    if ! command -v certbot &> /dev/null; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Obtention du certificat
    certbot --nginx \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        -m "admin@dazno.de" \
        --redirect
    
    success "✓ SSL configuré avec succès"
}

# Fonction principale
main() {
    info "=== Début du déploiement MCP sur Hostinger ==="
    
    validate_environment
    backup_current
    stop_services
    prepare_directories
    configure_nginx
    configure_env
    deploy_docker
    check_health
    configure_ssl
    
    success "=== Déploiement terminé avec succès ==="
    
    echo
    echo "🌐 Points d'accès:"
    echo "  • API: https://$DOMAIN"
    echo "  • Documentation: https://$DOMAIN/docs"
    echo "  • Santé: https://$DOMAIN/health"
    echo
    echo "📊 Monitoring:"
    echo "  • Métriques: https://$DOMAIN/metrics"
    echo
    echo "📝 Logs:"
    echo "  • Journal de déploiement: $LOG_FILE"
    echo "  • Sauvegarde: $BACKUP_DIR"
    echo
    echo "💡 Commandes utiles:"
    echo "  • Logs: docker-compose -f docker-compose.hostinger-production.yml logs -f"
    echo "  • Status: docker-compose -f docker-compose.hostinger-production.yml ps"
    echo "  • Restart: docker-compose -f docker-compose.hostinger-production.yml restart"
}

# Exécution
main "$@" 