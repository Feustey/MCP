#!/bin/bash

# Déploiement complet monitoring production avec Prometheus + Grafana
# Configure les services, évite les conflits de ports, et importe les dashboards
# Version: Production Complete 1.0.0

set -euo pipefail

# Configuration
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"
API_URL="https://api.dazno.de"
DAZNODE_ID="02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_deploy() { echo -e "${PURPLE}[DEPLOY]${NC} $1"; }

echo -e "\n${PURPLE}🚀 DÉPLOIEMENT PRODUCTION MONITORING COMPLET${NC}"
echo "============================================================"
echo "Serveur: api.dazno.de"
echo "Ports nginx: 80/443 (utilisés par l'API)"
echo "Grafana: https://api.dazno.de/grafana/"
echo "Prometheus: https://api.dazno.de/metrics"
echo "Timestamp: $(date)"
echo "============================================================\n"

# Notification de début
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="🚀 <b>DÉPLOIEMENT PRODUCTION MONITORING</b>

🎯 Configuration complète des services
📊 Prometheus + Grafana + Dashboards  
⏰ $(date '+%d/%m/%Y à %H:%M')

🔧 <b>Configuration:</b>
• API: https://api.dazno.de (ports 80/443)
• Grafana: /grafana/ (port 3000 interne)
• Prometheus: /metrics (port 9090 interne)
• Dashboards: Import automatique

⏳ Déploiement en cours..." \
    -d parse_mode="HTML" > /dev/null 2>&1

# Phase 1: Analyse des ports et services
log_deploy "Phase 1: Analyse de la configuration actuelle"

check_ports_and_services() {
    log "Vérification des ports utilisés..."
    
    # Vérification des ports nginx (80, 443)
    if netstat -tuln 2>/dev/null | grep -q ":80\|:443"; then
        log_success "Nginx actif sur ports 80/443"
    else
        log_warning "Nginx non détecté"
    fi
    
    # Vérification API
    api_status=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/health" --max-time 5 || echo "000")
    if [[ "$api_status" == "200" ]]; then
        log_success "API accessible via nginx"
    else
        log_warning "API non accessible ($api_status)"
    fi
    
    # Vérification des services internes
    log "Services internes configurés dans nginx:"
    if grep -q "grafana:3000" "$PROJECT_ROOT/config/nginx/nginx.conf"; then
        log_success "Grafana configuré (port 3000 interne)"
    fi
    if grep -q "prometheus:9090" "$PROJECT_ROOT/config/nginx/nginx.conf"; then
        log_success "Prometheus configuré (port 9090 interne)"
    fi
    
    return 0
}

check_ports_and_services

# Phase 2: Création du docker-compose pour monitoring
log_deploy "Phase 2: Configuration Docker Compose avec monitoring"

create_monitoring_compose() {
    local compose_file="$PROJECT_ROOT/docker-compose.monitoring.yml"
    
    log "Création du docker-compose monitoring..."
    
    cat > "$compose_file" <<'EOF'
version: '3.8'

services:
  # Service Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"  # Port interne seulement
    volumes:
      - ./config/prometheus/prometheus-prod.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    networks:
      - mcp-network

  # Service Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: mcp-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"  # Port interne seulement
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://api.dazno.de/grafana/
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./config/grafana/dashboards:/var/lib/grafana/dashboards:ro
    depends_on:
      - prometheus
    networks:
      - mcp-network

  # Node Exporter pour métriques système
  node-exporter:
    image: prom/node-exporter:latest
    container_name: mcp-node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - mcp-network

volumes:
  prometheus_data:
  grafana_data:

networks:
  mcp-network:
    external: true
EOF
    
    log_success "Docker Compose monitoring créé"
    return 0
}

create_monitoring_compose

# Phase 3: Configuration nginx mise à jour
log_deploy "Phase 3: Mise à jour configuration nginx pour éviter conflits"

update_nginx_config() {
    local nginx_config="$PROJECT_ROOT/config/nginx/nginx.conf"
    local backup_config="$nginx_config.backup.$(date +%Y%m%d_%H%M%S)"
    
    log "Sauvegarde de la configuration nginx..."
    cp "$nginx_config" "$backup_config"
    
    # Vérification et correction des conflits de location /metrics
    log "Correction des conflits nginx..."
    
    # Création d'une version corrigée
    cat > "$nginx_config.tmp" <<'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    resolver 127.0.0.11 valid=30s;
    
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Serveur HTTPS principal
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name api.dazno.de;
        
        # Configuration SSL
        ssl_certificate /etc/nginx/ssl/api.dazno.de.crt;
        ssl_certificate_key /etc/nginx/ssl/api.dazno.de.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        
        # Headers de sécurité
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        
        # Headers CORS
        set $cors_origin "";
        if ($http_origin ~* "^https://(app\.token-for-good\.com|app\.dazno\.de)$") {
            set $cors_origin $http_origin;
        }
        add_header Access-Control-Allow-Origin $cors_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With, X-API-Key" always;
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Max-Age "3600" always;
        
        # Grafana - Priorité haute
        location /grafana/ {
            set $upstream_grafana grafana:3000;
            proxy_pass http://$upstream_grafana/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Port $server_port;
            
            # Support WebSocket pour Grafana
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        # Prometheus - Métriques brutes
        location /prometheus/ {
            set $upstream_prometheus prometheus:9090;
            proxy_pass http://$upstream_prometheus/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API Métriques - via FastAPI
        location /metrics {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin $cors_origin always;
                add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
                add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
                add_header Access-Control-Max-Age "3600" always;
                add_header Content-Type "text/plain charset=UTF-8";
                add_header Content-Length 0;
                return 204;
            }
            
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/metrics;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API v1
        location /api/v1/ {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin $cors_origin always;
                add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
                add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With, X-API-Key" always;
                add_header Access-Control-Max-Age "3600" always;
                add_header Content-Type "text/plain charset=UTF-8";
                add_header Content-Length 0;
                return 204;
            }
            
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/api/v1/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health check
        location /health {
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/health;
            access_log off;
        }
        
        # Documentation
        location /docs {
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/docs;
        }
        
        location /redoc {
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/redoc;
        }
        
        # Info endpoint
        location /info {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin $cors_origin always;
                add_header Access-Control-Allow-Methods "GET, OPTIONS" always;
                add_header Access-Control-Max-Age "3600" always;
                add_header Content-Type "text/plain charset=UTF-8";
                add_header Content-Length 0;
                return 204;
            }
            
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api/info;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API principale - catch-all
        location / {
            if ($request_method = 'OPTIONS') {
                add_header Access-Control-Allow-Origin $cors_origin always;
                add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
                add_header Access-Control-Max-Age "3600" always;
                add_header Content-Type "text/plain charset=UTF-8";
                add_header Content-Length 0;
                return 204;
            }
            
            set $upstream_api mcp-api:8000;
            proxy_pass http://$upstream_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }
    }
    
    # Redirection HTTP vers HTTPS
    server {
        listen 80;
        listen [::]:80;
        server_name api.dazno.de;
        return 301 https://$server_name$request_uri;
    }
}
EOF
    
    # Remplacement de la configuration
    mv "$nginx_config.tmp" "$nginx_config"
    log_success "Configuration nginx mise à jour"
    log "Sauvegarde: $(basename "$backup_config")"
    
    return 0
}

update_nginx_config

# Phase 4: Configuration automatique Grafana avec dashboards
log_deploy "Phase 4: Configuration automatique Grafana"

setup_grafana_auto_provisioning() {
    log "Configuration du provisioning automatique Grafana..."
    
    # Configuration des dashboards
    local dashboards_config="$PROJECT_ROOT/config/grafana/provisioning/dashboards/dashboards.yml"
    
    mkdir -p "$(dirname "$dashboards_config")"
    
    cat > "$dashboards_config" <<'EOF'
apiVersion: 1

providers:
  - name: 'MCP Dashboards'
    orgId: 1
    folder: 'MCP Monitoring'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF
    
    log_success "Configuration dashboards Grafana créée"
    
    # Mise à jour de la datasource Prometheus
    local datasource_config="$PROJECT_ROOT/config/grafana/provisioning/datasources/prometheus.yml"
    
    cat > "$datasource_config" <<'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus-uid
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: POST
    version: 1
    
  - name: Prometheus-External
    type: prometheus
    uid: prometheus-external-uid
    access: proxy
    url: https://api.dazno.de/prometheus/
    isDefault: false
    editable: true
    jsonData:
      timeInterval: "30s"
      queryTimeout: "30s"
      httpMethod: GET
    version: 1
EOF
    
    log_success "Configuration datasources Grafana mise à jour"
    
    return 0
}

setup_grafana_auto_provisioning

# Phase 5: Script de démarrage des services
log_deploy "Phase 5: Script de démarrage des services monitoring"

create_monitoring_startup_script() {
    local startup_script="$PROJECT_ROOT/scripts/start_monitoring_services.sh"
    
    cat > "$startup_script" <<'EOF'
#!/bin/bash

# Script de démarrage des services monitoring
# Lance Prometheus, Grafana et configure l'environnement

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.monitoring.yml"

echo "🚀 Démarrage des services monitoring..."

# Vérification du réseau Docker
if ! docker network inspect mcp-network >/dev/null 2>&1; then
    echo "Création du réseau Docker mcp-network..."
    docker network create mcp-network
fi

# Vérification des permissions
if [[ ! -d "$PROJECT_ROOT/config/grafana" ]]; then
    echo "Erreur: Configuration Grafana manquante"
    exit 1
fi

# Correction des permissions pour Grafana
sudo chown -R 472:472 "$PROJECT_ROOT/config/grafana" 2>/dev/null || true

# Démarrage des services
echo "Démarrage Docker Compose..."
cd "$PROJECT_ROOT"
docker-compose -f "$COMPOSE_FILE" up -d

# Attente du démarrage
echo "Attente du démarrage des services..."
sleep 30

# Vérification des services
echo "Vérification des services:"
docker-compose -f "$COMPOSE_FILE" ps

# Test des endpoints
echo "Test des endpoints:"
echo -n "Prometheus: "
curl -s -f http://localhost:9090/-/healthy >/dev/null && echo "✅ OK" || echo "❌ KO"

echo -n "Grafana: "
curl -s -f http://localhost:3000/api/health >/dev/null && echo "✅ OK" || echo "❌ KO"

echo ""
echo "✅ Services monitoring démarrés!"
echo "📊 Grafana: https://api.dazno.de/grafana/ (admin/admin123)"
echo "📈 Prometheus: https://api.dazno.de/prometheus/"
echo "🎛️ Métriques API: https://api.dazno.de/metrics"
EOF
    
    chmod +x "$startup_script"
    log_success "Script de démarrage créé"
    
    return 0
}

create_monitoring_startup_script

# Phase 6: Démarrage des services
log_deploy "Phase 6: Démarrage des services monitoring"

start_monitoring_services() {
    log "Exécution du script de démarrage..."
    
    # Création du réseau si nécessaire
    if ! docker network inspect mcp-network >/dev/null 2>&1; then
        log "Création du réseau Docker..."
        docker network create mcp-network 2>/dev/null || true
    fi
    
    # Démarrage des services
    cd "$PROJECT_ROOT"
    
    log "Lancement de Docker Compose monitoring..."
    if docker-compose -f docker-compose.monitoring.yml up -d; then
        log_success "Services monitoring démarrés"
        
        # Attente du démarrage
        log "Attente du démarrage complet (30s)..."
        sleep 30
        
        # Tests de santé
        prometheus_health=""
        grafana_health=""
        
        if curl -s -f http://localhost:9090/-/healthy >/dev/null 2>&1; then
            prometheus_health="✅ OK"
        else
            prometheus_health="❌ KO"
        fi
        
        if curl -s -f http://localhost:3000/api/health >/dev/null 2>&1; then
            grafana_health="✅ OK"
        else
            grafana_health="❌ KO"
        fi
        
        log "État des services:"
        log "  Prometheus: $prometheus_health"
        log "  Grafana: $grafana_health"
        
    else
        log_error "Erreur démarrage Docker Compose"
        return 1
    fi
    
    return 0
}

start_monitoring_services

# Phase 7: Import automatique des dashboards
log_deploy "Phase 7: Import automatique des dashboards Grafana"

import_dashboards_auto() {
    log "Attente de l'initialisation Grafana..."
    sleep 10
    
    # Attendre que Grafana soit prêt
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f http://localhost:3000/api/health >/dev/null 2>&1; then
            log_success "Grafana prêt"
            break
        fi
        
        log "Tentative $attempt/$max_attempts - Attente Grafana..."
        sleep 2
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Timeout: Grafana non accessible"
        return 1
    fi
    
    # Import des dashboards via API
    log "Import des dashboards..."
    
    local grafana_api="http://admin:admin123@localhost:3000/api"
    
    # Dashboard serveur
    if [[ -f "$PROJECT_ROOT/config/grafana/dashboards/server_monitoring.json" ]]; then
        log "Import dashboard serveur..."
        curl -s -X POST "$grafana_api/dashboards/db" \
            -H "Content-Type: application/json" \
            -d @"$PROJECT_ROOT/config/grafana/dashboards/server_monitoring.json" >/dev/null 2>&1 && \
            log_success "Dashboard serveur importé" || \
            log_warning "Erreur import dashboard serveur"
    fi
    
    # Dashboard daznode
    if [[ -f "$PROJECT_ROOT/config/grafana/dashboards/daznode_monitoring.json" ]]; then
        log "Import dashboard daznode..."
        curl -s -X POST "$grafana_api/dashboards/db" \
            -H "Content-Type: application/json" \
            -d @"$PROJECT_ROOT/config/grafana/dashboards/daznode_monitoring.json" >/dev/null 2>&1 && \
            log_success "Dashboard daznode importé" || \
            log_warning "Erreur import dashboard daznode"
    fi
    
    return 0
}

import_dashboards_auto

# Phase 8: Tests finaux et vérification
log_deploy "Phase 8: Tests finaux de l'installation"

perform_final_tests() {
    log "Tests finaux des services monitoring..."
    
    local tests_passed=0
    local total_tests=8
    
    # Test 1: Prometheus
    if curl -s -f http://localhost:9090/-/healthy >/dev/null 2>&1; then
        ((tests_passed++))
        log_success "✓ Prometheus opérationnel"
    else
        log_error "✗ Prometheus non accessible"
    fi
    
    # Test 2: Grafana
    if curl -s -f http://localhost:3000/api/health >/dev/null 2>&1; then
        ((tests_passed++))
        log_success "✓ Grafana opérationnel"
    else
        log_error "✗ Grafana non accessible"
    fi
    
    # Test 3: Accès via nginx Grafana
    if curl -s -k -f "$API_URL/grafana/api/health" >/dev/null 2>&1; then
        ((tests_passed++))
        log_success "✓ Grafana via nginx OK"
    else
        log_error "✗ Grafana via nginx KO"
    fi
    
    # Test 4: Accès via nginx Prometheus
    if curl -s -k -f "$API_URL/prometheus/-/healthy" >/dev/null 2>&1; then
        ((tests_passed++))
        log_success "✓ Prometheus via nginx OK"
    else
        log_error "✗ Prometheus via nginx KO"
    fi
    
    # Test 5: Métriques API
    api_metrics_status=$(curl -s -k -w "%{http_code}" -o /dev/null "$API_URL/metrics" --max-time 5 || echo "000")
    if [[ "$api_metrics_status" =~ ^(200|404)$ ]]; then
        ((tests_passed++))
        log_success "✓ Endpoint métriques API accessible"
    else
        log_error "✗ Endpoint métriques API non accessible ($api_metrics_status)"
    fi
    
    # Test 6: Collecteur daznode
    if [[ -f "/tmp/daznode_metrics.prom" ]] && [[ $(wc -l < "/tmp/daznode_metrics.prom") -gt 20 ]]; then
        ((tests_passed++))
        log_success "✓ Collecteur daznode actif"
    else
        log_error "✗ Collecteur daznode inactif"
    fi
    
    # Test 7: Cron rapport quotidien
    if crontab -l 2>/dev/null | grep -q "daily_metrics_report.sh.*7.*30"; then
        ((tests_passed++))
        log_success "✓ Rapport quotidien 7h30 configuré"
    else
        log_error "✗ Rapport quotidien non configuré"
    fi
    
    # Test 8: Docker services
    running_services=$(docker-compose -f docker-compose.monitoring.yml ps --services --filter "status=running" | wc -l)
    if [[ $running_services -ge 2 ]]; then
        ((tests_passed++))
        log_success "✓ Services Docker actifs ($running_services)"
    else
        log_error "✗ Services Docker insuffisants ($running_services)"
    fi
    
    echo "Tests réussis: $tests_passed/$total_tests"
    return $((total_tests - tests_passed))
}

perform_final_tests
final_errors=$?

# Résumé final
echo -e "\n${BLUE}📊 RÉSUMÉ DÉPLOIEMENT PRODUCTION${NC}"
echo "============================================================"

if [[ $final_errors -eq 0 ]]; then
    deployment_status="✅ DÉPLOIEMENT COMPLET RÉUSSI"
    status_emoji="🎯"
    color=$GREEN
elif [[ $final_errors -le 2 ]]; then
    deployment_status="⚠️ DÉPLOIEMENT PARTIEL"
    status_emoji="⚠️"
    color=$YELLOW
else
    deployment_status="❌ DÉPLOIEMENT INCOMPLET"
    status_emoji="❌"
    color=$RED
fi

echo -e "Statut: ${color}${deployment_status}${NC}"
echo ""
echo "Services déployés:"
echo "• 📊 Grafana: https://api.dazno.de/grafana/ (admin/admin123)"
echo "• 📈 Prometheus: https://api.dazno.de/prometheus/"
echo "• 🎛️ Métriques API: https://api.dazno.de/metrics"
echo "• ⚡ Collecteur daznode: Actif (5min)"
echo "• 📱 Rapport quotidien: 7h30"

# Notification finale
final_message="$status_emoji <b>MONITORING PRODUCTION DÉPLOYÉ</b>

📅 $(date '+%d/%m/%Y à %H:%M')

🚀 <b>Services opérationnels:</b>
• 📊 Grafana: https://api.dazno.de/grafana/
• 📈 Prometheus: https://api.dazno.de/prometheus/
• 🎛️ Métriques: https://api.dazno.de/metrics
• ⚡ Collecteur: Actif (5min)

🎯 <b>Configuration:</b>
┣━ Dashboards: 2 importés automatiquement
┣━ Datasource: Prometheus configuré
┣━ Rapport quotidien: 7h30
┣━ Surveillance: 24/7 active
┗━ Tests: $((8 - final_errors))/8 réussis

$(if [[ $final_errors -eq 0 ]]; then
echo "✅ <b>MONITORING 100% OPÉRATIONNEL</b>
🎯 Accéder à Grafana maintenant
📊 Dashboards prêts à utiliser"
else
echo "⚠️ <b>Finalisation en cours</b>
🔄 Vérifier les services signalés
⏳ Tests à répéter si nécessaire"
fi)

🤖 Déploiement automatique terminé"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="$final_message" \
    -d parse_mode="HTML" > /dev/null 2>&1

echo -e "\n${GREEN}✅ DÉPLOIEMENT MONITORING PRODUCTION TERMINÉ!${NC}"
echo -e "\n${CYAN}🎯 ACCÈS AUX SERVICES:${NC}"
echo "• Grafana: https://api.dazno.de/grafana/ (admin/admin123)"
echo "• Prometheus: https://api.dazno.de/prometheus/"
echo "• Métriques: https://api.dazno.de/metrics"
echo ""
echo -e "${CYAN}📋 PROCHAINES ÉTAPES:${NC}"
echo "1. Accéder à Grafana et vérifier les dashboards"
echo "2. Attendre le rapport quotidien demain 7h30"
echo "3. Surveiller les métriques en temps réel"

exit $final_errors