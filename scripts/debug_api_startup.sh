#!/bin/bash

# Script de debug du démarrage de l'API MCP
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

# Debug du démarrage de l'API
debug_api_startup() {
    info "Debug du démarrage de l'API MCP..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Logs détaillés de l'API MCP ==="
        docker logs mcp-api --tail=50
        
        echo -e "\n=== État du conteneur ==="
        docker inspect mcp-api --format='{{.State.Status}} - {{.State.Health.Status}}'
        
        echo -e "\n=== Test de connectivité interne ==="
        docker exec mcp-api curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API interne OK" || echo "❌ API interne KO"
        
        echo -e "\n=== Test de connectivité externe ==="
        curl -f http://localhost:8000/health 2>/dev/null && echo "✅ API externe OK" || echo "❌ API externe KO"
        
        echo -e "\n=== Vérification des processus dans le conteneur ==="
        docker exec mcp-api ps aux
        
        echo -e "\n=== Vérification des fichiers dans le conteneur ==="
        docker exec mcp-api ls -la /app/
        
        echo -e "\n=== Vérification des variables d'environnement ==="
        docker exec mcp-api env | grep -E "(LNBITS|MONGO|REDIS|OPENAI)" || echo "Aucune variable trouvée"
        
        echo -e "\n=== Test de démarrage manuel ==="
        docker exec mcp-api sh -c "cd /app && python -c 'import app.main; print(\"Module app.main OK\")'" 2>/dev/null && echo "✅ Module OK" || echo "❌ Module KO"
EOF
}

# Correction du démarrage de l'API
corriger_demarrage_api() {
    info "🔧 Correction du démarrage de l'API..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt de l'API ==="
        docker stop mcp-api
        docker rm mcp-api
        
        echo "=== Vérification du fichier .env ==="
        if [ -f ".env.production" ]; then
            cp .env.production .env
            echo "✅ Fichier .env créé"
        else
            echo "❌ Fichier .env.production non trouvé"
            exit 1
        fi
        
        echo "=== Rebuild de l'image API ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml build mcp-api
        
        echo "=== Démarrage de l'API ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.local.yml up -d mcp-api
        
        echo "=== Attente du démarrage ==="
        sleep 30
        
        echo "=== Logs après redémarrage ==="
        docker logs mcp-api --tail=20
EOF
}

# Création d'une API simple de test
creer_api_simple() {
    info "Création d'une API simple de test..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Création d'une API FastAPI simple ==="
        cat > app_simple.py << 'PYTHON_EOF'
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="MCP API Simple", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "MCP API Simple - OK", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-api", "version": "1.0.0"}

@app.get("/api/v1/status")
async def status():
    return {"status": "running", "version": "1.0.0", "service": "mcp-api"}

@app.get("/docs")
async def docs():
    return {"message": "Documentation disponible sur /docs"}
PYTHON_EOF

        echo "=== Création du docker-compose simple ==="
        cat > docker-compose.api-simple.yml << 'COMPOSE_EOF'
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

# Démarrage de l'API simple
demarrer_api_simple() {
    info "Démarrage de l'API simple..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt des services existants ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        
        echo "=== Démarrage de l'API simple ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.api-simple.yml up -d
        
        echo "=== Attente du démarrage ==="
        sleep 30
        
        echo "=== Vérification des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.api-simple.yml ps
        
        echo "=== Test de l'API simple ==="
        for i in {1..5}; do
            if curl -f http://localhost:8000/health 2>/dev/null; then
                echo "✅ API simple accessible"
                curl http://localhost:8000/health
                break
            else
                echo "⏳ Tentative $i/5 - API non accessible, attente..."
                sleep 10
            fi
        done
        
        echo "=== Logs de l'API simple ==="
        docker logs mcp-api --tail=10
EOF
}

# Test de l'API
test_api() {
    info "Test de l'API..."
    
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
    echo "Debug du démarrage de l'API MCP"
    echo "================================="
    
    debug_api_startup
    
    read -p "Voulez-vous essayer de corriger l'API? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        corriger_demarrage_api
        
        read -p "Voulez-vous essayer l'API simple si la correction échoue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            creer_api_simple
            demarrer_api_simple
        fi
        
        test_api
        
        success "🎉 Debug terminé!"
        echo ""
        echo " URLs d'accès:"
        echo "   API: https://api.dazno.de"
        echo "   Documentation: https://api.dazno.de/docs"
        echo "   Health: https://api.dazno.de/health"
    else
        info "❌ Debug annulé"
    fi
}

# Exécution du script
main "$@" 