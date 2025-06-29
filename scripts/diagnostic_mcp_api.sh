#!/bin/bash

# Script de diagnostic pour le conteneur MCP API
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

# Diagnostic complet
diagnostic_complet() {
    info "�� Diagnostic complet du conteneur MCP API..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== État des conteneurs ==="
        docker ps -a
        
        echo -e "\n=== Logs détaillés du conteneur mcp-api ==="
        docker logs mcp-api --tail=50 || echo "❌ Impossible de récupérer les logs"
        
        echo -e "\n=== Informations sur l'image ==="
        docker images | grep feustey || echo "❌ Image feustey non trouvée"
        
        echo -e "\n=== Vérification des volumes ==="
        docker volume ls
        
        echo -e "\n=== Vérification des réseaux ==="
        docker network ls
        
        echo -e "\n=== Vérification des fichiers de configuration ==="
        cd /home/feustey/feustey
        echo "Fichiers présents:"
        ls -la
        
        echo -e "\n=== Contenu du .env ==="
        if [ -f ".env" ]; then
            cat .env | head -10
        else
            echo "❌ Fichier .env non trouvé"
        fi
        
        echo -e "\n=== Vérification des ports ==="
        netstat -tlnp | grep -E ':(8000|8080|8443|3000|9090)' || echo "Aucun port en écoute"
        
        echo -e "\n=== Ressources système ==="
        df -h
        free -h
        
        echo -e "\n=== Tentative de démarrage manuel ==="
        echo "Arrêt du conteneur..."
        docker stop mcp-api || true
        docker rm mcp-api || true
        
        echo "Démarrage manuel avec logs..."
        cd /home/feustey/feustey
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up mcp-api
EOF
}

# Vérification des fichiers de configuration
verifier_configuration() {
    info "📋 Vérification des fichiers de configuration..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Vérification du Dockerfile ==="
        if [ -f "MCP/Dockerfile" ]; then
            echo "✅ Dockerfile trouvé"
            head -20 MCP/Dockerfile
        else
            echo "❌ Dockerfile non trouvé"
        fi
        
        echo -e "\n=== Vérification du docker-compose.local.yml ==="
        if [ -f "docker-compose.local.yml" ]; then
            echo "✅ docker-compose.local.yml trouvé"
            head -30 docker-compose.local.yml
        else
            echo "❌ docker-compose.local.yml non trouvé"
        fi
        
        echo -e "\n=== Vérification des scripts de démarrage ==="
        if [ -f "MCP/scripts/start.sh" ]; then
            echo "✅ start.sh trouvé"
            cat MCP/scripts/start.sh
        else
            echo "❌ start.sh non trouvé"
        fi
        
        if [ -f "MCP/scripts/entrypoint-prod.sh" ]; then
            echo "✅ entrypoint-prod.sh trouvé"
            head -10 MCP/scripts/entrypoint-prod.sh
        else
            echo "❌ entrypoint-prod.sh non trouvé"
        fi
EOF
}

# Test de démarrage simple
test_demarrage_simple() {
    info "🧪 Test de démarrage simple..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Test avec image Python simple ==="
        docker run --rm -d --name test-python -p 8001:8000 python:3.11-slim sh -c "
            pip install fastapi uvicorn &&
            echo 'from fastapi import FastAPI; app = FastAPI(); @app.get(\"/health\"); def health(): return {\"status\": \"ok\"}' > /tmp/app.py &&
            python -m uvicorn app:app --host 0.0.0.0 --port 8000
        "
        
        sleep 10
        
        echo "Test de l'API simple:"
        curl -f http://localhost:8001/health || echo "❌ API simple non accessible"
        
        docker stop test-python
EOF
}

# Correction du docker-compose
corriger_docker_compose() {
    info "🔧 Correction du docker-compose..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Création d'un docker-compose simplifié ==="
        cat > docker-compose.simple.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # API principale MCP - Version simplifiée
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
      - DEBUG=true
    networks:
      - mcp-network
    # Suppression du healthcheck pour le diagnostic
    # healthcheck:
    #   test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    #   interval: 30s
    #   timeout: 10s
    #   retries: 3

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

        echo "✅ docker-compose.simple.yml créé"
        
        echo "=== Arrêt des services existants ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        
        echo "=== Démarrage avec la version simplifiée ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml up -d
        
        echo "=== Attente et vérification ==="
        sleep 30
        
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml ps
        
        echo "=== Logs du conteneur mcp-api ==="
        docker logs mcp-api --tail=20
EOF
}

# Fonction principale
main() {
    echo "�� Diagnostic du conteneur MCP API"
    echo "=================================="
    
    diagnostic_complet
    verifier_configuration
    test_demarrage_simple
    
    read -p "Voulez-vous essayer la correction automatique? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        corriger_docker_compose
    fi
    
    success "�� Diagnostic terminé!"
}

# Exécution du script
main "$@" 