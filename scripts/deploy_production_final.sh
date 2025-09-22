#!/bin/bash

# Script de déploiement MCP Production Final
# Docker-compose unifié avec SSL, sans Grafana/Prometheus/Ollama
# Version: 1.0 - 27 août 2025

set -e
set -o pipefail

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
PROJECT_NAME="mcp-production"
REMOTE_HOST="feustey@147.79.101.32"
REMOTE_PATH="/home/feustey/mcp-production"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonction de log
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "========================================="
    echo "   MCP PRODUCTION DEPLOYMENT FINAL"
    echo "   Docker-compose unifié avec SSL"
    echo "   Sans Grafana/Prometheus/Ollama"
    echo "========================================="
    echo -e "${NC}"
}

# Vérification environnement local
check_local_environment() {
    log "Vérification environnement local..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
        exit 1
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Fichiers requis
    local required_files=(
        "$COMPOSE_FILE"
        "config/nginx/ssl-production.conf"
        "config/nginx/ssl/api.dazno.de.crt"
        "config/nginx/ssl/api.dazno.de.key"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    log "✓ Environnement local validé"
}

# Préparation des fichiers
prepare_deployment_files() {
    log "Préparation des fichiers de déploiement..."
    
    # Créer dossier temporaire
    mkdir -p /tmp/mcp-deploy
    
    # Copier les fichiers essentiels
    cp "$COMPOSE_FILE" /tmp/mcp-deploy/
    cp -r config /tmp/mcp-deploy/
    cp -r scripts /tmp/mcp-deploy/
    
    # Créer fichier .env de production
    cat > /tmp/mcp-deploy/.env << EOF
# MCP Production Environment
ENVIRONMENT=production
DEBUG=false

# Sécurité (A CHANGER EN PRODUCTION)
JWT_SECRET_KEY=prod_jwt_secret_$(date +%s)
SECRET_KEY=prod_secret_key_$(date +%s)  
SECURITY_SECRET_KEY=prod_security_secret_$(date +%s)

# Base de données MongoDB Atlas (Production)
MONGO_URL=mongodb+srv://feustey:sIiEp8oiB2hjYBbi@dazia.pin4fwl.mongodb.net/mcp?retryWrites=true&w=majority&appName=Dazia

# Redis Cloud (Production)  
REDIS_URL=redis://default:EqbM5xJAkh9gvdOyVoYiWR9EoHRBXcjY@redis-16818.crce202.eu-west-3-1.ec2.redns.redis-cloud.com:16818/0
REDIS_HOST=redis-16818.crce202.eu-west-3-1.ec2.redns.redis-cloud.com
REDIS_PORT=16818
REDIS_PASSWORD=EqbM5xJAkh9gvdOyVoYiWR9EoHRBXcjY
REDIS_USERNAME=default

# API Keys (Production)
ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY:-}
OPENAI_API_KEY=\${OPENAI_API_KEY:-}
AI_OPENAI_API_KEY=\${OPENAI_API_KEY:-}

# Lightning Network
LNBITS_URL=https://lnbits.dazno.de
LNBITS_ADMIN_KEY=\${LNBITS_ADMIN_KEY:-}
LNBITS_INKEY=\${LNBITS_INKEY:-3fbbe7e0c2a24b43aa2c6ad6627f44eb}

# APIs externes
SPARKSEER_API_KEY=\${SPARKSEER_API_KEY:-}

# Notifications
TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_CHAT_ID=\${TELEGRAM_CHAT_ID:-}

# Supabase  
SUPABASE_URL=\${SUPABASE_URL:-}
SUPABASE_ROLE=\${SUPABASE_ROLE:-}
EOF
    
    log "✓ Fichiers de déploiement préparés"
}

# Upload vers serveur
upload_to_server() {
    log "Upload vers serveur de production..."
    
    # Créer dossier distant
    ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PATH && mkdir -p $REMOTE_PATH/logs && mkdir -p $REMOTE_PATH/backups"
    
    # Synchroniser fichiers
    rsync -avz --delete \
        /tmp/mcp-deploy/ \
        "$REMOTE_HOST:$REMOTE_PATH/"
    
    # Créer dossiers de données
    ssh "$REMOTE_HOST" "cd $REMOTE_PATH && mkdir -p {mcp-data,t4g-data}/{logs,data,rag,backups,reports,uploads}"
    
    log "✓ Fichiers uploadés sur serveur"
}

# Déploiement distant
deploy_remote() {
    log "Déploiement sur serveur de production..."
    
    ssh "$REMOTE_HOST" << EOF
        cd $REMOTE_PATH
        
        # Arrêter anciens containers
        echo "Arrêt des anciens containers..."
        docker stop \$(docker ps -q) 2>/dev/null || true
        docker system prune -af
        
        # Déploiement
        echo "Démarrage des nouveaux services..."
        docker compose -f $COMPOSE_FILE up -d
        
        # Attendre stabilisation
        sleep 30
        
        # Vérifier état
        echo "=== État des containers ==="
        docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
EOF
    
    log "✓ Déploiement distant terminé"
}

# Vérification santé
health_check() {
    log "Vérification santé des services..."
    
    # Attendre stabilisation supplémentaire
    sleep 15
    
    # Tests via SSH
    ssh "$REMOTE_HOST" << 'EOF'
        echo "=== Tests de santé ==="
        
        # Test HTTP Health
        HTTP_HEALTH=$(curl -s http://localhost/health || echo "FAILED")
        echo "HTTP Health: $HTTP_HEALTH"
        
        # Test HTTPS Health  
        HTTPS_HEALTH=$(curl -k -s https://localhost/health || echo "FAILED")
        echo "HTTPS Health: $HTTPS_HEALTH"
        
        # Test redirection
        REDIRECT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "FAILED")
        echo "HTTP Redirect: $REDIRECT"
        
        # Vérifier logs nginx
        echo "=== Logs Nginx (dernières 5 lignes) ==="
        docker logs mcp-nginx-prod --tail 5 || echo "Pas de logs nginx"
        
        # État final
        echo "=== État final ==="
        docker ps | grep mcp || echo "Aucun container MCP trouvé"
EOF
    
    log "✓ Vérification santé terminée"
}

# Tests finaux
final_tests() {
    log "Tests finaux depuis l'extérieur..."
    
    # Test public (si accessible)
    info "Test endpoints publics:"
    
    # HTTP
    if curl -s -m 10 http://147.79.101.32/health >/dev/null 2>&1; then
        log "✓ HTTP public accessible"
    else
        warning "⚠ HTTP public non accessible (normal si firewall)"
    fi
    
    # HTTPS
    if curl -k -s -m 10 https://147.79.101.32/health >/dev/null 2>&1; then
        log "✓ HTTPS public accessible"  
    else
        warning "⚠ HTTPS public non accessible (normal si firewall)"
    fi
    
    log "✓ Tests finaux terminés"
}

# Nettoyage
cleanup() {
    log "Nettoyage..."
    rm -rf /tmp/mcp-deploy
    log "✓ Nettoyage terminé"
}

# Résumé final
show_summary() {
    echo ""
    echo -e "${GREEN}========================================="
    echo " DÉPLOIEMENT PRODUCTION TERMINÉ!"
    echo "=========================================${NC}"
    echo ""
    echo "Services déployés:"
    echo " - NGINX avec SSL (HTTP/HTTPS)"
    echo " - MCP API Principal"
    echo " - Qdrant (base vectorielle)"
    echo " - Service de backup"
    echo ""
    echo "Endpoints disponibles:"
    echo " - HTTP Health: http://147.79.101.32/health"
    echo " - HTTPS Health: https://147.79.101.32/health"  
    echo " - API MCP: https://147.79.101.32/api/v1/health"
    echo ""
    echo "Configuration:"
    echo " - SSL activé avec certificats"
    echo " - Redirection HTTP→HTTPS automatique"
    echo " - Ollama retiré du déploiement"
    echo " - Grafana/Prometheus désactivés"
    echo ""
    echo -e "${YELLOW}Note: Configurer les vraies clés API dans .env${NC}"
    echo ""
    echo "Commandes utiles sur le serveur:"
    echo " - docker ps : voir les containers"
    echo " - docker logs mcp-nginx-prod : logs nginx"
    echo " - docker logs mcp-api-prod : logs API"
    echo ""
}

# Fonction principale
main() {
    show_banner
    
    check_local_environment
    prepare_deployment_files
    upload_to_server
    deploy_remote
    health_check
    final_tests
    cleanup
    
    show_summary
}

# Gestion des erreurs
trap 'error "Une erreur est survenue. Nettoyage..."; cleanup; exit 1' ERR

# Confirmation avant déploiement
echo -e "${YELLOW}Êtes-vous prêt à déployer MCP en production ? (y/N)${NC}"
read -r CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Déploiement annulé."
    exit 0
fi

# Lancement
main "$@"