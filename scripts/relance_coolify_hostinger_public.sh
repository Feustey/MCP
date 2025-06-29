#!/bin/bash

# Script de relance Coolify sur Hostinger - Version avec build depuis GitHub public
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
REMOTE_DIR="/home/$REMOTE_USER/feustey"
SSH_KEY="/Users/stephanecourant/.ssh/id_ed25519"
SSH_OPTIONS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30"
SUDO_PWD="Feustey@AI!"
GITHUB_REPO="https://github.com/Feustey/MCP.git"
GITHUB_BRANCH="berty"

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
    echo -e "[${timestamp}] [${level}] ${message}"
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

# Vérification de la connectivité SSH
check_connectivity() {
    info "Vérification de la connectivité SSH vers Hostinger..."
    
    if ! ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" "echo 'Connexion SSH OK'" &> /dev/null; then
        error "❌ Échec de la connexion SSH vers $REMOTE_USER@$REMOTE_HOST"
    fi
    
    success "✅ Connectivité SSH OK"
}

# Préparation de l'environnement sur le serveur
prepare_environment() {
    info "🔧 Préparation de l'environnement sur le serveur..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
        cd /home/feustey
        
        # Créer le répertoire de travail
        mkdir -p feustey
        cd feustey
        
        # Cloner le repository public depuis la branche berty
        if [ ! -d "MCP" ]; then
            echo "📥 Clonage du repository MCP depuis la branche $GITHUB_BRANCH..."
            git clone -b $GITHUB_BRANCH $GITHUB_REPO MCP
        else
            echo "📥 Mise à jour du repository MCP..."
            cd MCP
            git fetch origin
            git reset --hard origin/$GITHUB_BRANCH
            cd ..
        fi
        
        # Copier les fichiers de configuration
        if [ -f "MCP/.env.production" ]; then
            cp MCP/.env.production .env.production
        fi
        
        # Créer les répertoires nécessaires
        mkdir -p {logs,data,config/{nginx,prometheus,grafana}}
        
        echo "✅ Environnement préparé"
EOF
}

# Création du docker-compose avec build local
create_local_compose() {
    info "Création du docker-compose avec build local..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        # Créer un docker-compose.yml avec build local
        cat > docker-compose.local.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # API principale MCP - Build depuis le code source
  mcp-api:
    build:
      context: ./MCP
      dockerfile: Dockerfile
    container_name: mcp-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data:ro
      - ./logs:/app/logs
      - ./rag:/app/rag:ro
    env_file:
      - .env.production
    environment:
      - TZ=Europe/Paris
      - PYTHONUNBUFFERED=1
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx pour le reverse proxy
  nginx:
    image: nginx:alpine
    container_name: mcp-nginx
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "8443:443"
    volumes:
      - ./config/nginx/api.dazno.de.conf:/etc/nginx/conf.d/default.conf:ro
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - mcp-api
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus pour la collecte de métriques
  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - mcp-network
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'

  # Grafana pour la visualisation
  grafana:
    image: grafana/grafana:latest
    container_name: mcp-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/dashboards:ro
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
    networks:
      - mcp-network
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

volumes:
  prometheus_data:
  grafana_data:

networks:
  mcp-network:
    driver: bridge
COMPOSE_EOF

        echo "✅ docker-compose.local.yml créé"
EOF
}

# Arrêt des services existants
stop_services() {
    info "Arrêt des services existants..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
        cd /home/feustey/feustey
        
        # Arrêt de tous les conteneurs
        echo "$SUDO_PWD" | sudo -S docker-compose down --remove-orphans || true
        echo "$SUDO_PWD" | sudo -S docker-compose -f docker-compose.local.yml down --remove-orphans || true
        
        # Arrêt forcé des conteneurs par nom
        docker stop mcp-api mcp-nginx mcp-prometheus mcp-grafana 2>/dev/null || true
        docker rm mcp-api mcp-nginx mcp-prometheus mcp-grafana 2>/dev/null || true
        
        echo "✅ Services arrêtés"
EOF
}

# Build et relance des services
build_and_restart() {
    info "🚀 Build et relance des services..."
    
    # Transférer le fichier .env.production
    scp $SSH_OPTIONS ".env.production" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/.env.production"
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        # Vérifier que le fichier .env.production existe
        if [ ! -f ".env.production" ]; then
            echo "❌ Fichier .env.production non trouvé"
            exit 1
        fi
        
        # Copier vers .env pour docker-compose
        cp .env.production .env
        
        # Build de l'image MCP
        echo "Build de l'image MCP..."
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml build mcp-api
        
        # Démarrage des services
        echo "🌟 Démarrage des services..."
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up -d
        
        # Attendre que les services démarrent
        echo "⏳ Attente du démarrage des services..."
        sleep 60
        
        # Vérification des services
        echo "✅ Vérification du déploiement..."
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml ps
        
        # Test de l'API
        echo "Test de l'API..."
        for attempt in {1..10}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API accessible"
                break
            else
                echo "⏳ Tentative $attempt/10 - API non accessible, attente..."
                sleep 15
            fi
        done
        
        # Affichage des logs récents
        echo "📝 Logs récents:"
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml logs --tail=30
EOF
}

# Test de l'API
test_api() {
    info "Test de l'API..."
    
    # Test via le domaine
    if curl -f https://api.dazno.de/health 2>/dev/null; then
        success "✅ API accessible via https://api.dazno.de"
    else
        warn "⚠️  API non accessible via le domaine"
    fi
}

# Fonction principale
main() {
    echo "Relance de Coolify sur Hostinger - Build depuis GitHub public"
    echo "============================================================="
    
    check_connectivity
    prepare_environment
    create_local_compose
    stop_services
    
    read -p "Voulez-vous continuer avec le build et la relance? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "❌ Relance annulée"
        exit 0
    fi
    
    build_and_restart
    test_api
    
    success "🎉 Relance terminée!"
    echo "Dashboard Grafana: http://147.79.101.32:3000"
    echo "📊 Prometheus: http://147.79.101.32:9090"
    echo "API: https://api.dazno.de"
}

# Exécution du script
main "$@" 