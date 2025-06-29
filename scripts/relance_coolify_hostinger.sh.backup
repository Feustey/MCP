#!/bin/bash

# Script de relance Coolify sur Hostinger
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
REMOTE_DIR="/home/$REMOTE_USER/feustey"
SSH_KEY="/Users/stephanecourant/.ssh/id_ed25519"
SSH_OPTIONS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30"
SUDO_PWD="Feustey@AI!"

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

# Vérification de la connectivité SSH uniquement
check_connectivity() {
    info "🔍 Vérification de la connectivité SSH vers Hostinger..."
    
    if ! ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" "echo 'Connexion SSH OK'" &> /dev/null; then
        error "❌ Échec de la connexion SSH vers $REMOTE_USER@$REMOTE_HOST"
    fi
    
    success "✅ Connectivité SSH OK"
}

# Diagnostic des services
diagnose_services() {
    info "🔍 Diagnostic des services sur Hostinger..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== État des conteneurs Docker ==="
        docker ps -a
        
        echo -e "\n=== Logs des conteneurs MCP ==="
        if docker ps | grep -q "mcp-api"; then
            docker logs --tail=20 mcp-api
        else
            echo "❌ Conteneur mcp-api non trouvé"
        fi
        
        echo -e "\n=== Utilisation des ressources ==="
        df -h
        free -h
        
        echo -e "\n=== Services système ==="
        systemctl status docker --no-pager || true
        systemctl status nginx --no-pager || true
        
        echo -e "\n=== Ports en écoute ==="
        netstat -tlnp | grep -E ':(80|443|8000|8080|8443|3000|9090)' || true
EOF
}

# Arrêt forcé des services
force_stop_services() {
    info "🛑 Arrêt forcé des services..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
        cd "$REMOTE_DIR"
        
        # Arrêt de tous les conteneurs MCP
        echo "$SUDO_PWD" | sudo -S docker-compose down --remove-orphans || true
        echo "$SUDO_PWD" | sudo -S docker-compose -f docker-compose.hostinger-production.yml down --remove-orphans || true
        
        # Arrêt forcé des conteneurs par nom
        docker stop mcp-api mcp-nginx mcp-prometheus mcp-grafana 2>/dev/null || true
        docker rm mcp-api mcp-nginx mcp-prometheus mcp-grafana 2>/dev/null || true
        
        # Nettoyage des conteneurs orphelins
        echo "$SUDO_PWD" | sudo -S docker system prune -f
        
        # Redémarrage du service Docker si nécessaire
        echo "$SUDO_PWD" | sudo -S systemctl restart docker
        
        echo "✅ Services arrêtés et nettoyés"
EOF
}

# Vérification et création du fichier .env.production
check_env_file() {
    info "📋 Vérification du fichier .env.production..."
    
    # Vérifier si le fichier existe localement
    if [ ! -f ".env.production" ]; then
        warn "⚠️  Fichier .env.production non trouvé localement"
        
        # Créer le fichier à partir du template
        if [ -f "config/env.production.template" ]; then
            info "📝 Création du fichier .env.production à partir du template..."
            cp config/env.production.template .env.production
            warn "⚠️  Veuillez configurer les variables dans .env.production avant de continuer"
            echo "Variables à configurer:"
            echo "   - MONGO_ROOT_PASSWORD"
            echo "   - SPARKSEER_API_KEY"
            echo "   - TELEGRAM_BOT_TOKEN"
            echo "   - TELEGRAM_CHAT_ID"
            read -p "Appuyez sur Entrée après avoir configuré le fichier .env.production..."
        else
            error "❌ Template .env.production.template non trouvé"
        fi
    fi
    
    success "✅ Fichier .env.production vérifié"
}

# Relance des services
restart_services() {
    info "🚀 Relance des services..."
    
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
        
        # Pull des images Docker
        echo "📥 Récupération des images Docker..."
        echo "Feustey@AI!" | sudo -S docker-compose pull
        
        # Démarrage des services
        echo "🌟 Démarrage des services..."
        echo "Feustey@AI!" | sudo -S docker-compose up -d
        
        # Attendre que les services démarrent
        echo "⏳ Attente du démarrage des services..."
        sleep 30
        
        # Vérification des services
        echo "✅ Vérification du déploiement..."
        echo "Feustey@AI!" | sudo -S docker-compose ps
        
        # Test de l'API
        echo "🔍 Test de l'API..."
        for attempt in {1..5}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API accessible"
                break
            else
                echo "⏳ Tentative $attempt/5 - API non accessible, attente..."
                sleep 10
            fi
        done
        
        # Affichage des logs récents
        echo "📝 Logs récents:"
        echo "Feustey@AI!" | sudo -S docker-compose logs --tail=20
EOF
}

# Test de l'API
test_api() {
    info "🔍 Test de l'API..."
    
    # Test via le domaine
    if curl -f https://api.dazno.de/health 2>/dev/null; then
        success "✅ API accessible via https://api.dazno.de"
    else
        warn "⚠️  API non accessible via le domaine"
    fi
}

# Fonction principale
main() {
    echo "🚀 Relance de Coolify sur Hostinger"
    echo "=================================="
    
    check_connectivity
    diagnose_services
    check_env_file
    
    read -p "Voulez-vous continuer avec la relance? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "❌ Relance annulée"
        exit 0
    fi
    
    force_stop_services
    restart_services
    test_api
    
    success "🎉 Relance terminée!"
    echo "📈 Dashboard Grafana: http://147.79.101.32:3000"
    echo "📈 Prometheus: http://147.79.101.32:9090"
    echo "🔍 API: https://api.dazno.de"
}

# Exécution du script
main "$@" 