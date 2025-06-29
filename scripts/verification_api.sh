#!/bin/bash

# Script de vérification de l'API MCP
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
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
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Vérification détaillée de l'API
verifier_api() {
    info "🔍 Vérification détaillée de l'API..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== État des conteneurs ==="
        docker ps
        
        echo -e "\n=== Logs détaillés du conteneur mcp-api ==="
        docker logs mcp-api --tail=30
        
        echo -e "\n=== Test de connectivité interne ==="
        docker exec mcp-api curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API accessible depuis l'intérieur du conteneur" || echo "❌ API non accessible depuis l'intérieur"
        
        echo -e "\n=== Test de connectivité depuis l'hôte ==="
        curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API accessible depuis l'hôte" || echo "❌ API non accessible depuis l'hôte"
        
        echo -e "\n=== Vérification des ports ==="
        netstat -tlnp | grep 8000 || echo "Port 8000 non en écoute"
        
        echo -e "\n=== Vérification des processus dans le conteneur ==="
        docker exec mcp-api ps aux
        
        echo -e "\n=== Vérification des fichiers dans le conteneur ==="
        docker exec mcp-api ls -la /app/
        
        echo -e "\n=== Test de démarrage manuel dans le conteneur ==="
        docker exec mcp-api sh -c "cd /app && python -c 'import app.main; print(\"Module app.main importé avec succès\")'" 2>/dev/null && echo "✅ Module app.main OK" || echo "❌ Erreur d'import du module"
EOF
}

# Correction des variables d'environnement manquantes
corriger_variables_env() {
    info "🔧 Correction des variables d'environnement..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Ajout des variables manquantes ==="
        
        # Vérifier et ajouter AI_OPENAI_API_KEY
        if ! grep -q "AI_OPENAI_API_KEY" .env.production; then
            echo "AI_OPENAI_API_KEY=sk-dummy-key-for-testing" >> .env.production
            echo "✅ AI_OPENAI_API_KEY ajoutée"
        fi
        
        # Vérifier et ajouter REDIS_HOST
        if ! grep -q "REDIS_HOST" .env.production; then
            echo "REDIS_HOST=redis" >> .env.production
            echo "✅ REDIS_HOST ajoutée"
        fi
        
        # Vérifier et ajouter MONGO_URL
        if ! grep -q "MONGO_URL" .env.production; then
            echo "MONGO_URL=mongodb://localhost:27017/mcp" >> .env.production
            echo "✅ MONGO_URL ajoutée"
        fi
        
        echo "=== Variables d'environnement mises à jour ==="
        grep -E "(AI_OPENAI_API_KEY|REDIS_HOST|MONGO_URL)" .env.production || echo "Aucune variable trouvée"
EOF
}

# Redémarrage avec nouvelles variables
redemarrer_avec_variables() {
    info "🚀 Redémarrage avec nouvelles variables..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Copie du fichier .env ==="
        cp .env.production .env
        
        echo "=== Arrêt des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml down
        
        echo "=== Rebuild de l'image ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml build mcp-api
        
        echo "=== Démarrage des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up -d
        
        echo "=== Attente du démarrage ==="
        sleep 45
        
        echo "=== Vérification des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml ps
        
        echo "=== Test de l'API ==="
        for attempt in {1..10}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API accessible"
                break
            else
                echo "⏳ Tentative $attempt/10 - API non accessible, attente..."
                sleep 15
            fi
        done
        
        echo "=== Logs récents ==="
        docker logs mcp-api --tail=20
EOF
}

# Test de l'API finale
test_api_finale() {
    info "🧪 Test de l'API finale..."
    
    # Test local
    if curl -f http://localhost:8000/health 2>/dev/null; then
        success "✅ API accessible localement"
    else
        warn "⚠️  API non accessible localement"
    fi
    
    # Test via le domaine
    if curl -f https://api.dazno.de/health 2>/dev/null; then
        success "✅ API accessible via https://api.dazno.de"
    else
        warn "⚠️  API non accessible via le domaine"
    fi
}

# Fonction principale
main() {
    echo "🔍 Vérification et correction de l'API MCP"
    echo "========================================="
    
    verifier_api
    corriger_variables_env
    
    read -p "Voulez-vous redémarrer avec les nouvelles variables? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        redemarrer_avec_variables
        test_api_finale
    fi
    
    success "🎉 Vérification terminée!"
    echo " Dashboard Grafana: http://147.79.101.32:3000"
    echo "📈 Prometheus: http://147.79.101.32:9090"
    echo " API: https://api.dazno.de"
}

# Exécution du script
main "$@" 