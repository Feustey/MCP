#!/bin/bash

# Script de correction du niveau de log pour MCP API
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

# Correction du niveau de log
corriger_log_level() {
    info "🔧 Correction du niveau de log..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml down --remove-orphans || true
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml down --remove-orphans || true
        
        echo "=== Correction du fichier .env.production ==="
        if [ -f ".env.production" ]; then
            # Remplacer LOG_LEVEL=INFO par LOG_LEVEL=info
            sed -i 's/LOG_LEVEL=INFO/LOG_LEVEL=info/g' .env.production
            sed -i 's/LOG_LEVEL=DEBUG/LOG_LEVEL=debug/g' .env.production
            sed -i 's/LOG_LEVEL=WARNING/LOG_LEVEL=warning/g' .env.production
            sed -i 's/LOG_LEVEL=ERROR/LOG_LEVEL=error/g' .env.production
            
            echo "✅ Niveau de log corrigé dans .env.production"
            echo "Nouveau LOG_LEVEL:"
            grep LOG_LEVEL .env.production || echo "LOG_LEVEL non trouvé"
        else
            echo "❌ Fichier .env.production non trouvé"
        fi
        
        echo "=== Correction du script de démarrage ==="
        if [ -f "MCP/scripts/start.sh" ]; then
            # Remplacer les niveaux de log en majuscules par des minuscules
            sed -i 's/--log-level INFO/--log-level info/g' MCP/scripts/start.sh
            sed -i 's/--log-level DEBUG/--log-level debug/g' MCP/scripts/start.sh
            sed -i 's/--log-level WARNING/--log-level warning/g' MCP/scripts/start.sh
            sed -i 's/--log-level ERROR/--log-level error/g' MCP/scripts/start.sh
            
            echo "✅ Script de démarrage corrigé"
            echo "Contenu du script start.sh:"
            cat MCP/scripts/start.sh
        else
            echo "❌ Script start.sh non trouvé"
        fi
        
        echo "=== Correction du script entrypoint ==="
        if [ -f "MCP/scripts/entrypoint-prod.sh" ]; then
            # Remplacer les niveaux de log en majuscules par des minuscules
            sed -i 's/--log-level INFO/--log-level info/g' MCP/scripts/entrypoint-prod.sh
            sed -i 's/--log-level DEBUG/--log-level debug/g' MCP/scripts/entrypoint-prod.sh
            sed -i 's/--log-level WARNING/--log-level warning/g' MCP/scripts/entrypoint-prod.sh
            sed -i 's/--log-level ERROR/--log-level error/g' MCP/scripts/entrypoint-prod.sh
            
            echo "✅ Script entrypoint corrigé"
        else
            echo "❌ Script entrypoint-prod.sh non trouvé"
        fi
EOF
}

# Redémarrage des services
redemarrer_services() {
    info "🚀 Redémarrage des services..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Copie du fichier .env ==="
        cp .env.production .env
        
        echo "=== Rebuild de l'image ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml build mcp-api
        
        echo "=== Démarrage des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up -d
        
        echo "=== Attente du démarrage ==="
        sleep 30
        
        echo "=== Vérification des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml ps
        
        echo "=== Test de l'API ==="
        for attempt in {1..5}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API accessible"
                break
            else
                echo "⏳ Tentative $attempt/5 - API non accessible, attente..."
                sleep 10
            fi
        done
        
        echo "=== Logs récents ==="
        docker logs mcp-api --tail=10
EOF
}

# Test de l'API
test_api() {
    info "🧪 Test de l'API..."
    
    # Test via le domaine
    if curl -f https://api.dazno.de/health 2>/dev/null; then
        success "✅ API accessible via https://api.dazno.de"
    else
        warn "⚠️  API non accessible via le domaine"
    fi
}

# Fonction principale
main() {
    echo "🔧 Correction du niveau de log MCP API"
    echo "====================================="
    
    corriger_log_level
    redemarrer_services
    test_api
    
    success "🎉 Correction terminée!"
    echo "🔗 Dashboard Grafana: http://147.79.101.32:3000"
    echo "📈 Prometheus: http://147.79.101.32:9090"
    echo "🌐 API: https://api.dazno.de"
}

# Exécution du script
main "$@" 