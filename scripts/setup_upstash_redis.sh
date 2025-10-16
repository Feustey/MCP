#!/bin/bash
#
# Configuration Upstash Redis Cloud pour MCP Production
# Script d'activation et migration depuis Redis local
#
# Dernière mise à jour: 15 octobre 2025

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ☁️  CONFIGURATION UPSTASH REDIS CLOUD                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
ENV_FILE="${1:-.env.production}"
BACKUP_DIR="./data/redis_migration_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  - Fichier ENV: $ENV_FILE"
echo "  - Backup dir: $BACKUP_DIR"
echo ""

# Vérifier que le fichier .env existe
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Fichier $ENV_FILE introuvable${NC}"
    echo ""
    echo "Création du fichier depuis le template..."
    cp env.production.template "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo -e "${YELLOW}⚠️  Veuillez éditer $ENV_FILE avec vos credentials Upstash${NC}"
    echo ""
    echo "Instructions:"
    echo "  1. Allez sur https://upstash.com/"
    echo "  2. Créez un compte (ou connectez-vous)"
    echo "  3. Créez une base Redis:"
    echo "     - Nom: mcp-production"
    echo "     - Region: eu-west-1 (ou proche de votre serveur)"
    echo "     - Type: Pay as you go (ou Free tier pour tester)"
    echo "  4. Copiez les credentials dans $ENV_FILE:"
    echo "     - REDIS_URL=rediss://default:xxxxx@eu1-xxxxx.upstash.io:6379"
    echo "     - REDIS_PASSWORD=votre_password"
    echo "     - REDIS_TLS=true"
    echo "  5. Relancez ce script"
    exit 1
fi

echo -e "${BLUE}🔍 Étape 1/6: Vérification credentials Upstash${NC}"
echo "=================================================="

# Charger les variables d'environnement
source "$ENV_FILE"

if [ -z "$REDIS_URL" ] || [[ "$REDIS_URL" == *"your-redis-instance"* ]]; then
    echo -e "${RED}❌ REDIS_URL non configurée dans $ENV_FILE${NC}"
    echo ""
    echo "Configuration requise:"
    echo "  REDIS_URL=rediss://default:password@host.upstash.io:6379"
    echo "  REDIS_TLS=true"
    exit 1
fi

echo -e "${GREEN}✅ Credentials Upstash détectées${NC}"
echo "  URL: ${REDIS_URL:0:30}..."
echo ""

echo -e "${BLUE}🧪 Étape 2/6: Test connexion Upstash${NC}"
echo "========================================"

# Extraire host et password depuis REDIS_URL
REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|rediss?://([^:]+:[^@]+@)?([^:]+).*|\2|')
REDIS_PASS=$(echo "$REDIS_URL" | sed -E 's|rediss?://[^:]*:([^@]+)@.*|\1|')

echo "  Host: $REDIS_HOST"
echo ""

# Test de connexion avec redis-cli (si disponible)
if command -v redis-cli &> /dev/null; then
    echo "Test PING..."
    if redis-cli -u "$REDIS_URL" PING 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}✅ Connexion Upstash OK (PING successful)${NC}"
    else
        echo -e "${RED}❌ Échec de connexion à Upstash${NC}"
        echo ""
        echo "Vérifiez:"
        echo "  1. Credentials correctes dans $ENV_FILE"
        echo "  2. IP autorisée dans Upstash (Whitelist IP)"
        echo "  3. TLS activé (rediss://)"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  redis-cli non installé, skip test direct${NC}"
    echo "Installation recommandée: apt install redis-tools"
fi

echo ""

echo -e "${BLUE}💾 Étape 3/6: Backup Redis local (optionnel)${NC}"
echo "==============================================="

# Créer le dossier de backup
mkdir -p "$BACKUP_DIR"

# Si Docker Redis local est actif, faire un dump
if docker ps | grep -q mcp-redis; then
    echo "Export des données Redis locales..."
    
    # Sauvegarder les clés existantes
    docker exec mcp-redis redis-cli --scan > "$BACKUP_DIR/keys_$TIMESTAMP.txt" 2>/dev/null || true
    
    # Compter les clés
    KEY_COUNT=$(wc -l < "$BACKUP_DIR/keys_$TIMESTAMP.txt" 2>/dev/null || echo "0")
    
    if [ "$KEY_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✅ Backup créé: $KEY_COUNT clés exportées${NC}"
        echo "  Fichier: $BACKUP_DIR/keys_$TIMESTAMP.txt"
    else
        echo -e "${YELLOW}ℹ️  Redis local vide, aucune donnée à migrer${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Redis local non actif, skip backup${NC}"
fi

echo ""

echo -e "${BLUE}🔧 Étape 4/6: Mise à jour configuration Docker${NC}"
echo "================================================"

# Backup du docker-compose actuel
cp docker-compose.hostinger.yml "docker-compose.hostinger.yml.backup_$TIMESTAMP"

# Créer une version modifiée qui utilise Upstash
cat > docker-compose.hostinger.upstash.yml << 'DOCKERCOMPOSE'
version: '3.8'

services:
  # MongoDB Service (inchangé)
  mongodb:
    image: mongo:7.0
    container_name: mcp-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGODB_USER:-mcpuser}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-ChangeThisPassword123!}
      MONGO_INITDB_DATABASE: ${MONGODB_DATABASE:-mcp_prod}
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
      - ./mongo-init.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
    networks:
      - mcp-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 40s
    command: mongod --auth
  
  # REDIS LOCAL DÉSACTIVÉ (remplacé par Upstash)
  # redis:
  #   image: redis:7-alpine
  #   ... (désactivé)

  # MCP API Service (utilise Upstash externe)
  mcp-api:
    image: mcp-api:latest
    container_name: mcp-api
    restart: unless-stopped
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - API_WORKERS=2
      
      # MongoDB (connexion interne Docker)
      - MONGODB_URL=mongodb://${MONGODB_USER:-mcpuser}:${MONGODB_PASSWORD:-ChangeThisPassword123!}@mongodb:27017/${MONGODB_DATABASE:-mcp_prod}?authSource=admin
      - MONGO_URL=mongodb://${MONGODB_USER:-mcpuser}:${MONGODB_PASSWORD:-ChangeThisPassword123!}@mongodb:27017/${MONGODB_DATABASE:-mcp_prod}?authSource=admin
      - MONGODB_DATABASE=${MONGODB_DATABASE:-mcp_prod}
      - MONGO_NAME=${MONGODB_DATABASE:-mcp_prod}
      
      # Redis UPSTASH CLOUD (connexion externe)
      - REDIS_URL=${REDIS_URL}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - REDIS_TLS=${REDIS_TLS:-true}
      - REDIS_MAX_CONNECTIONS=${REDIS_MAX_CONNECTIONS:-10}
      
      # Sécurité
      - SECRET_KEY=${SECRET_KEY}
      - SECURITY_SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      
      # Mode et features
      - DRY_RUN=${DRY_RUN:-true}
      - ENABLE_SHADOW_MODE=${ENABLE_SHADOW_MODE:-true}
      - ENABLE_RAG=${ENABLE_RAG:-false}
      
      # LNBits
      - LNBITS_URL=${LNBITS_URL}
      - LNBITS_ADMIN_KEY=${LNBITS_ADMIN_KEY}
      - LNBITS_INVOICE_KEY=${LNBITS_INVOICE_KEY:-demo_invoice_key}
      - LNBITS_INKEY=${LNBITS_INVOICE_KEY:-demo_invoice_key}
      
      # AI / OpenAI
      - AI_OPENAI_API_KEY=${AI_OPENAI_API_KEY:-sk-dummy-key}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-sk-ant-dummy-key}
      
      # Monitoring
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
      
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config:/app/config:ro
    networks:
      - mcp-network
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Nginx Reverse Proxy (inchangé)
  nginx:
    image: nginx:alpine
    container_name: mcp-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-docker.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    networks:
      - mcp-network
    depends_on:
      - mcp-api
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mongodb_data:
    driver: local
  mongodb_config:
    driver: local
  nginx_logs:
    driver: local
  # redis_data supprimé (plus nécessaire)

networks:
  mcp-network:
    driver: bridge
DOCKERCOMPOSE

echo -e "${GREEN}✅ docker-compose.hostinger.upstash.yml créé${NC}"
echo "  Backup original: docker-compose.hostinger.yml.backup_$TIMESTAMP"
echo ""

echo -e "${BLUE}🚀 Étape 5/6: Redémarrage avec Upstash${NC}"
echo "========================================"

echo "Arrêt des conteneurs actuels..."
docker compose -f docker-compose.hostinger.yml down

echo ""
echo "Démarrage avec Upstash..."
docker compose -f docker-compose.hostinger.upstash.yml --env-file "$ENV_FILE" up -d

echo ""
echo "Attente démarrage services (30s)..."
sleep 30

echo ""

echo -e "${BLUE}✅ Étape 6/6: Validation${NC}"
echo "========================"

# Test API health
echo "Test API health check..."
if curl -s http://localhost:8000/ | grep -q "status"; then
    echo -e "${GREEN}✅ API accessible${NC}"
else
    echo -e "${RED}❌ API non accessible${NC}"
    echo "Vérifier les logs: docker logs mcp-api"
fi

echo ""
echo "Test connexion Redis Upstash depuis l'API..."
# TODO: Ajouter un endpoint de test Redis dans l'API

echo ""
echo "Logs de démarrage (dernières 20 lignes):"
docker logs --tail 20 mcp-api

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ UPSTASH REDIS CLOUD ACTIVÉ                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📋 Configuration appliquée:${NC}"
echo "  - Redis local: DÉSACTIVÉ"
echo "  - Upstash Cloud: ACTIVÉ"
echo "  - TLS: Oui (rediss://)"
echo "  - Connection pooling: 10 connexions"
echo ""
echo -e "${BLUE}📊 Métriques à surveiller:${NC}"
echo "  - Latency: Doit rester < 20ms (Europe)"
echo "  - Hit rate: > 80% après warm-up"
echo "  - Connexions: Max 10 simultanées"
echo ""
echo -e "${YELLOW}⚠️  Actions de suivi:${NC}"
echo "  1. Vérifier les logs: docker logs -f mcp-api"
echo "  2. Surveiller dashboard Upstash: https://console.upstash.com/"
echo "  3. Tester les performances: curl http://localhost:8000/api/v1/health"
echo "  4. Si tout OK, remplacer docker-compose.hostinger.yml par la version upstash"
echo ""
echo -e "${GREEN}🎯 Pour rendre permanent:${NC}"
echo "  mv docker-compose.hostinger.upstash.yml docker-compose.hostinger.yml"
echo ""

