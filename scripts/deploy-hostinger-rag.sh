#!/bin/bash
# Script de déploiement MCP RAG sur Hostinger
# Dernière mise à jour: 7 janvier 2025

set -e

# Configuration
PROJECT_NAME="mcp-rag"
DOCKER_IMAGE="feustey/dazno:latest"
DOMAIN="api.dazno.de"
SSH_HOST="feustey@147.79.101.32"  # À remplacer par vos vraies credentials
SSH_PORT="22"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    # Vérifier SSH
    if ! command -v ssh &> /dev/null; then
        error "SSH n'est pas installé"
    fi
    
    # Vérifier que l'image Docker existe
    if ! docker image inspect $DOCKER_IMAGE &> /dev/null; then
        warn "Image Docker $DOCKER_IMAGE non trouvée localement"
        log "Tentative de pull depuis Docker Hub..."
        docker pull $DOCKER_IMAGE
    fi
    
    log "Prérequis vérifiés avec succès"
}

# Création du docker-compose pour Hostinger
create_docker_compose() {
    log "Création du docker-compose.yml pour Hostinger..."
    
    cat > docker-compose.hostinger.yml << EOF
version: '3.8'

services:
  mcp-api:
    image: $DOCKER_IMAGE
    container_name: mcp-api-hostinger
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # Configuration de base
      - ENVIRONMENT=production
      - DEBUG=false
      - DRY_RUN=true
      - LOG_LEVEL=INFO
      
      # Configuration serveur
      - HOST=0.0.0.0
      - PORT=8000
      - RELOAD=false
      - WORKERS=4
      
      # Base de données MongoDB (Hostinger)
      - MONGO_URL=mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhU@localhost:27017/mcp?authSource=admin&retryWrites=true&w=majority
      
      # Redis (Hostinger)
      - REDIS_URL=redis://localhost:6379/0
      
      # Sécurité
      - JWT_SECRET_KEY=your-jwt-secret-key-here
      - SECRET_KEY=your-secret-key-here
      
      # Services externes
      - LNBITS_URL=https://lnbits.dazno.de
      - LNBITS_ADMIN_KEY=your-lnbits-admin-key
      
      # RAG et Intelligence
      - OLLAMA_URL=http://localhost:11434
      - ANTHROPIC_API_KEY=your-anthropic-api-key
      
      # Monitoring
      - PROMETHEUS_ENABLED=true
      - GRAFANA_ENABLED=true
      
      # SSL/TLS
      - SSL_ENABLED=true
      - SSL_CERT_PATH=/etc/ssl/certs/api.dazno.de.crt
      - SSL_KEY_PATH=/etc/ssl/private/api.dazno.de.key
      
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./rag:/app/rag
      - ./backups:/app/backups
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro
      
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
      
    networks:
      - mcp-network

  nginx:
    image: nginx:alpine
    container_name: mcp-nginx-hostinger
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/api.dazno.de.conf:/etc/nginx/conf.d/default.conf:ro
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - mcp-api
    networks:
      - mcp-network

  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus-hostinger
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus/prometheus-prod.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - mcp-network

  grafana:
    image: grafana/grafana:latest
    container_name: mcp-grafana-hostinger
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on:
      - prometheus
    networks:
      - mcp-network

  qdrant:
    image: qdrant/qdrant:latest
    container_name: mcp-qdrant-hostinger
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
      - ./config/qdrant/config.yaml:/qdrant/config/config.yaml:ro
    networks:
      - mcp-network

volumes:
  prometheus_data:
  grafana_data:
  qdrant_data:

networks:
  mcp-network:
    driver: bridge
EOF

    log "docker-compose.hostinger.yml créé"
}

# Création des répertoires nécessaires
create_directories() {
    log "Création des répertoires sur le serveur..."
    
    ssh -p $SSH_PORT $SSH_HOST << 'EOF'
        mkdir -p ~/mcp-rag/{logs,data,rag,backups,config/{nginx,prometheus,grafana,qdrant}}
        mkdir -p ~/mcp-rag/logs/{nginx,api}
        mkdir -p ~/mcp-rag/data/{metrics,reports,actions}
        mkdir -p ~/mcp-rag/rag/{RAG_assets,generators,integrations}
        mkdir -p ~/mcp-rag/config/grafana/{dashboards,provisioning/{datasources,dashboards}}
        mkdir -p ~/mcp-rag/config/prometheus/rules
        chmod -R 755 ~/mcp-rag
EOF
    
    log "Répertoires créés sur le serveur"
}

# Upload des fichiers de configuration
upload_config_files() {
    log "Upload des fichiers de configuration..."
    
    # Upload du docker-compose
    scp -P $SSH_PORT docker-compose.hostinger.yml $SSH_HOST:~/mcp-rag/
    
    # Upload des configurations nginx
    scp -P $SSH_PORT config/nginx/api.dazno.de.conf $SSH_HOST:~/mcp-rag/config/nginx/
    scp -P $SSH_PORT config/nginx/nginx.conf $SSH_HOST:~/mcp-rag/config/nginx/
    
    # Upload des configurations prometheus
    scp -P $SSH_PORT config/prometheus/prometheus-prod.yml $SSH_HOST:~/mcp-rag/config/prometheus/prometheus.yml
    scp -P $SSH_PORT config/prometheus/rules/mcp_alerts.yml $SSH_HOST:~/mcp-rag/config/prometheus/rules/
    
    # Upload des configurations grafana
    scp -P $SSH_PORT config/grafana/dashboards/mcp_overview.json $SSH_HOST:~/mcp-rag/config/grafana/dashboards/
    scp -P $SSH_PORT config/grafana/provisioning/dashboards/mcp.yml $SSH_HOST:~/mcp-rag/config/grafana/provisioning/dashboards/
    scp -P $SSH_PORT config/grafana/provisioning/datasources/prometheus.yml $SSH_HOST:~/mcp-rag/config/grafana/provisioning/datasources/
    
    # Upload de la configuration qdrant
    scp -P $SSH_PORT config/qdrant/config.yaml $SSH_HOST:~/mcp-rag/config/qdrant/
    
    log "Fichiers de configuration uploadés"
}

# Déploiement sur le serveur
deploy_on_server() {
    log "Déploiement sur le serveur Hostinger..."
    
    ssh -p $SSH_PORT $SSH_HOST << 'EOF'
        cd ~/mcp-rag
        
        # Arrêt des conteneurs existants
        docker-compose -f docker-compose.hostinger.yml down || true
        
        # Nettoyage des images non utilisées
        docker image prune -f
        
        # Pull de la dernière image
        docker pull feustey/dazno:latest
        
        # Démarrage des services
        docker-compose -f docker-compose.hostinger.yml up -d
        
        # Attente du démarrage
        sleep 30
        
        # Vérification de la santé
        echo "Vérification de la santé des services..."
        docker-compose -f docker-compose.hostinger.yml ps
        
        # Test de l'API
        echo "Test de l'API..."
        curl -f http://localhost:8000/api/v1/health || echo "API non accessible"
        
        # Test des endpoints RAG
        echo "Test des endpoints RAG..."
        curl -f http://localhost:8000/api/v1/rag/health || echo "RAG non accessible"
        
        # Test des endpoints Intelligence
        echo "Test des endpoints Intelligence..."
        curl -f http://localhost:8000/api/v1/intelligence/health/intelligence || echo "Intelligence non accessible"
EOF
    
    log "Déploiement terminé"
}

# Vérification post-déploiement
post_deployment_check() {
    log "Vérification post-déploiement..."
    
    # Test de l'API publique
    log "Test de l'API publique sur $DOMAIN..."
    if curl -f https://$DOMAIN/api/v1/health; then
        log "✅ API publique accessible"
    else
        warn "⚠️ API publique non accessible"
    fi
    
    # Test des endpoints RAG
    log "Test des endpoints RAG..."
    if curl -f https://$DOMAIN/api/v1/rag/health; then
        log "✅ Endpoints RAG accessibles"
    else
        warn "⚠️ Endpoints RAG non accessibles"
    fi
    
    # Test des endpoints Intelligence
    log "Test des endpoints Intelligence..."
    if curl -f https://$DOMAIN/api/v1/intelligence/health/intelligence; then
        log "✅ Endpoints Intelligence accessibles"
    else
        warn "⚠️ Endpoints Intelligence non accessibles"
    fi
    
    log "Vérification post-déploiement terminée"
}

# Affichage des informations de déploiement
show_deployment_info() {
    log "Informations de déploiement:"
    echo ""
    echo "🌐 API publique: https://$DOMAIN"
    echo "📊 Documentation: https://$DOMAIN/docs"
    echo "📈 Grafana: https://$DOMAIN:3000 (admin/admin123)"
    echo "📊 Prometheus: https://$DOMAIN:9090"
    echo ""
    echo "🧠 Endpoints RAG: https://$DOMAIN/api/v1/rag"
    echo "🧠 Endpoints Intelligence: https://$DOMAIN/api/v1/intelligence"
    echo ""
    echo "📋 Logs: ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml logs -f'"
    echo "🔄 Redémarrage: ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml restart'"
    echo "🛑 Arrêt: ssh $SSH_HOST 'cd ~/mcp-rag && docker-compose -f docker-compose.hostinger.yml down'"
    echo ""
}

# Fonction principale
main() {
    log "🚀 Démarrage du déploiement MCP RAG sur Hostinger"
    log "Image Docker: $DOCKER_IMAGE"
    log "Domaine: $DOMAIN"
    log "Serveur: $SSH_HOST"
    echo ""
    
    check_prerequisites
    create_docker_compose
    create_directories
    upload_config_files
    deploy_on_server
    post_deployment_check
    show_deployment_info
    
    log "✅ Déploiement MCP RAG terminé avec succès!"
}

# Gestion des erreurs
trap 'error "Erreur lors du déploiement"' ERR

# Exécution
main "$@" 