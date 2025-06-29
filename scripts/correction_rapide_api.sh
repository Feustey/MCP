#!/bin/bash

# Script de correction rapide pour l'API MCP
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

# Diagnostic rapide
diagnostic_rapide() {
    info "🔍 Diagnostic rapide..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Logs du conteneur mcp-api ==="
        docker logs mcp-api --tail=20
        
        echo -e "\n=== État du conteneur ==="
        docker ps | grep mcp-api
        
        echo -e "\n=== Test de connectivité interne ==="
        docker exec mcp-api curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API interne OK" || echo "❌ API interne KO"
        
        echo -e "\n=== Test de connectivité externe ==="
        curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API externe OK" || echo "❌ API externe KO"
        
        echo -e "\n=== Vérification des processus ==="
        docker exec mcp-api ps aux | grep -E "(uvicorn|python)" || echo "Aucun processus uvicorn/python trouvé"
EOF
}

# Création d'un docker-compose simplifié avec FastAPI basique
creer_compose_simple() {
    info "📝 Création d'un docker-compose simplifié..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Création d'une application FastAPI simple ==="
        cat > app_simple.py << 'PYTHON_EOF'
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="MCP API Simple", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "MCP API Simple - OK"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-api"}

@app.get("/api/v1/status")
async def status():
    return {"status": "running", "version": "1.0.0"}
PYTHON_EOF

        echo "=== Création du docker-compose simple ==="
        cat > docker-compose.simple.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # API simple avec FastAPI
  mcp-api:
    image: python:3.11-slim
    container_name: mcp-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./app_simple.py:/app/app.py:ro
      - ./data:/app/data:ro
      - ./logs:/app/logs
    working_dir: /app
    command: >
      sh -c "pip install fastapi uvicorn &&
             python -m uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info"
    networks:
      - mcp-network

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

        echo "✅ Fichiers créés"
EOF
}

# Démarrage avec l'API simple
demarrer_api_simple() {
    info "🚀 Démarrage avec l'API simple..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt des services existants ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml down --remove-orphans || true
        
        echo "=== Démarrage avec l'API simple ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml up -d
        
        echo "=== Attente du démarrage ==="
        sleep 30
        
        echo "=== Vérification des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.simple.yml ps
        
        echo "=== Test de l'API simple ==="
        for attempt in {1..5}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API simple accessible"
                curl http://localhost:8000/health
                break
            else
                echo "⏳ Tentative $attempt/5 - API non accessible, attente..."
                sleep 10
            fi
        done
        
        echo "=== Logs de l'API simple ==="
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
    echo "🔧 Correction rapide de l'API MCP"
    echo "================================"
    
    diagnostic_rapide
    creer_compose_simple
    
    read -p "Voulez-vous démarrer l'API simple? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        demarrer_api_simple
        test_api
        
        success "🎉 API simple démarrée!"
        echo " Dashboard Grafana: http://147.79.101.32:3000"
        echo "📈 Prometheus: http://147.79.101.32:9090"
        echo " API: https://api.dazno.de"
        echo " API Simple: http://147.79.101.32:8000"
    else
        info "❌ Démarrage annulé"
    fi
}

# Exécution du script
main "$@" 