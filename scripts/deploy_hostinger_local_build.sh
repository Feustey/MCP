#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-api"
IMAGE_TAG="latest"
REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"
DOCKER_COMPOSE_FILE="docker-compose.hostinger-local.yml"

# Couleurs pour les logs
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Début du déploiement local vers Hostinger${NC}"

# Sauvegarde du répertoire de travail original
ORIGINAL_DIR=$(pwd)

# Configuration Docker avec timeouts plus longs
export DOCKER_CLIENT_TIMEOUT=120
export COMPOSE_HTTP_TIMEOUT=120

# Préparation du contexte de build
echo "🔧 Préparation du contexte de build..."
BUILD_CONTEXT="/tmp/mcp-build"
rm -rf $BUILD_CONTEXT
mkdir -p $BUILD_CONTEXT

# Copie des fichiers nécessaires
cp Dockerfile.api $BUILD_CONTEXT/Dockerfile
cp requirements.txt $BUILD_CONTEXT/
cp -r app $BUILD_CONTEXT/
cp -r src $BUILD_CONTEXT/

# Build de l'image avec des options de timeout
echo "📦 Construction de l'image Docker..."
cd $BUILD_CONTEXT
DOCKER_BUILDKIT=1 docker build \
    --network=host \
    --platform linux/amd64 \
    --progress=plain \
    --build-arg BUILDKIT_STEP_TIMEOUT=600 \
    -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Sauvegarde et transfert (dans le répertoire de build)
echo "💾 Sauvegarde de l'image..."
docker save ${IMAGE_NAME}:${IMAGE_TAG} | gzip > mcp_image.tar.gz

# Transfert vers Hostinger
echo "📤 Transfert vers Hostinger..."
scp -P ${REMOTE_PORT} mcp_image.tar.gz ${REMOTE_USER}@${REMOTE_HOST}:/tmp/

# Retour au répertoire original
cd $ORIGINAL_DIR

# Création et configuration des répertoires sur Hostinger
echo "📁 Création et configuration des répertoires sur Hostinger..."
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Nettoyage et création des répertoires
    rm -rf /opt/mcp/config/nginx
    mkdir -p /opt/mcp/config/nginx
    chown -R root:root /opt/mcp
    chmod -R 755 /opt/mcp
    
    # Création du fichier de configuration Nginx
    cat > /opt/mcp/config/nginx/api.dazno.de.conf << 'NGINX_CONF'
server {
    listen 8080;
    server_name api.dazno.de;
    
    # Redirection forcée vers HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.dazno.de;
    
    # Certificats SSL Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;
    
    # Health check public (sans rate limiting)
    location = /health {
        proxy_pass http://mcp-api-hostinger:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Pas de rate limiting pour health check
        access_log off;
    }
    
    # API principale
    location / {
        proxy_pass http://mcp-api-hostinger:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_CONF

    # Vérification du fichier
    ls -l /opt/mcp/config/nginx/api.dazno.de.conf
    cat /opt/mcp/config/nginx/api.dazno.de.conf
EOF

# Transfert du docker-compose
echo "📤 Transfert du docker-compose..."
scp -P ${REMOTE_PORT} ${DOCKER_COMPOSE_FILE} ${REMOTE_USER}@${REMOTE_HOST}:/opt/mcp/

# Déploiement sur Hostinger
echo "🚀 Déploiement sur Hostinger..."
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Configuration Docker avec timeouts plus longs
    export DOCKER_CLIENT_TIMEOUT=120
    export COMPOSE_HTTP_TIMEOUT=120
    
    cd /tmp
    docker load < mcp_image.tar.gz
    rm mcp_image.tar.gz
    cd /opt/mcp
    mkdir -p logs data rag
    docker-compose -f docker-compose.hostinger-local.yml up -d
EOF

echo -e "${GREEN}✅ Déploiement terminé avec succès${NC}"

# Vérification des endpoints
echo -e "${GREEN}🔍 Vérification des endpoints...${NC}"
echo "API: https://api.dazno.de"
echo "MongoDB: mongodb://${REMOTE_HOST}:27017"
echo "Redis: redis://${REMOTE_HOST}:6379"