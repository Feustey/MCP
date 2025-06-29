#!/bin/bash

# Script de correction de l'erreur 502 sur l'API MCP
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

# Diagnostic de l'erreur 502
diagnostic_502() {
    info "🔍 Diagnostic de l'erreur 502..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== État des conteneurs ==="
        docker ps -a
        
        echo -e "\n=== Services en cours d'exécution ==="
        docker ps
        
        echo -e "\n=== Ports en écoute ==="
        netstat -tlnp | grep -E ':(80|443|8000|8080|8443|5000)' || echo "Aucun port trouvé"
        
        echo -e "\n=== Test de l'API locale ==="
        curl -f http://localhost:8000/health && echo " ✅ API locale OK" || echo " ❌ API locale KO"
        
        echo -e "\n=== Test de Nginx ==="
        curl -f http://localhost:8080 && echo " ✅ Nginx OK" || echo " ❌ Nginx KO"
        
        echo -e "\n=== Logs Nginx ==="
        docker logs mcp-nginx --tail=10 2>/dev/null || echo "Conteneur mcp-nginx non trouvé"
        
        echo -e "\n=== Logs API ==="
        docker logs mcp-api --tail=10 2>/dev/null || echo "Conteneur mcp-api non trouvé"
        
        echo -e "\n=== Configuration Nginx ==="
        if [ -f "config/nginx/api.dazno.de.conf" ]; then
            cat config/nginx/api.dazno.de.conf
        else
            echo "❌ Configuration Nginx non trouvée"
        fi
EOF
}

# Redémarrage des services MCP
redemarrer_services_mcp() {
    info "🚀 Redémarrage des services MCP..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt de tous les services ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml down --remove-orphans || true
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.lnbits-simple.yml down --remove-orphans || true
        
        echo "=== Nettoyage des conteneurs ==="
        docker stop $(docker ps -q) 2>/dev/null || true
        docker rm $(docker ps -aq) 2>/dev/null || true
        
        echo "=== Redémarrage de l'API MCP ==="
        if [ -f "docker-compose.local.yml" ]; then
            echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up -d
        elif [ -f "docker-compose.simple.yml" ]; then
            echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml up -d
        else
            echo "❌ Aucun fichier docker-compose trouvé"
            exit 1
        fi
        
        echo "=== Attente du démarrage ==="
        sleep 30
        
        echo "=== Vérification des services ==="
        docker ps
        
        echo "=== Test de l'API ==="
        for i in {1..5}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API accessible"
                break
            else
                echo "⏳ Tentative $i/5 - API non accessible, attente..."
                sleep 10
            fi
        done
EOF
}

# Correction de la configuration Nginx
corriger_nginx() {
    info "🔧 Correction de la configuration Nginx..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Création de la configuration Nginx ==="
        mkdir -p config/nginx
        
        cat > config/nginx/api.dazno.de.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name api.dazno.de;
    
    # Redirection vers HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.dazno.de;
    
    # Configuration SSL (à adapter selon votre setup)
    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;
    
    # Configuration SSL sécurisée
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Headers de sécurité
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy vers l'API MCP
    location / {
        proxy_pass http://mcp-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        proxy_pass http://mcp-api:8000/health;
        access_log off;
    }
    
    # Documentation
    location /docs {
        proxy_pass http://mcp-api:8000/docs;
    }
    
    # OpenAPI
    location /openapi.json {
        proxy_pass http://mcp-api:8000/openapi.json;
    }
    
    # Métriques
    location /metrics {
        proxy_pass http://mcp-api:8000/metrics;
        access_log off;
    }
}
NGINX_EOF

        echo "✅ Configuration Nginx créée"
        
        # Redémarrer Nginx si nécessaire
        if docker ps | grep -q "mcp-nginx"; then
            echo "=== Redémarrage de Nginx ==="
            docker restart mcp-nginx
        fi
EOF
}

# Test de l'API
test_api() {
    info "🧪 Test de l'API..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Test complet de l'API ==="
        
        echo "1. Test API locale:"
        curl -f http://localhost:8000/health && echo " ✅" || echo " ❌"
        
        echo "2. Test Nginx local:"
        curl -f http://localhost:8080 && echo " ✅" || echo " ❌"
        
        echo "3. Test via IP:"
        curl -f http://147.79.101.32:8000/health && echo " ✅" || echo " ❌"
        
        echo "4. Test via domaine:"
        curl -f https://api.dazno.de/health && echo " ✅" || echo " ❌"
        
        echo "5. Test documentation:"
        curl -f https://api.dazno.de/docs && echo " ✅" || echo " ❌"
EOF
}

# Fonction principale
main() {
    echo "🔧 Correction de l'erreur 502 sur l'API MCP"
    echo "========================================="
    
    diagnostic_502
    
    read -p "Voulez-vous redémarrer les services MCP? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        redemarrer_services_mcp
        corriger_nginx
        test_api
        
        success "🎉 Correction terminée!"
        echo ""
        echo " URLs d'accès:"
        echo "   🚀 API: https://api.dazno.de"
        echo "   📚 Documentation: https://api.dazno.de/docs"
        echo "   🏥 Health: https://api.dazno.de/health"
    else
        info "❌ Correction annulée"
    fi
}

# Exécution du script
main "$@" 