#!/bin/bash

# Script de déploiement complet MCP sur serveur distant
# Usage: ./deploy_complete.sh

set -e

echo "🚀 Déploiement MCP sur serveur distant..."

# Configuration
SERVER="feustey@147.79.101.32"
REMOTE_DIR="/tmp/mcp-deploy"
LOCAL_SCRIPT="scripts/deploy_simple_fix.sh"

echo "📤 Transfert du script de déploiement..."
scp "$LOCAL_SCRIPT" "$SERVER:/tmp/"

echo "🔧 Exécution du déploiement sur le serveur..."
ssh "$SERVER" << 'EOF'
set -e

echo "🔍 Vérification de l'environnement..."
cd /tmp

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker non installé"
    exit 1
fi

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose non installé"
    exit 1
fi

echo "✅ Docker et Docker Compose disponibles"

# Arrêter les services existants
echo "🛑 Arrêt des services existants..."
docker-compose -f /tmp/mcp-deploy/docker-compose.yml down 2>/dev/null || true
docker stop mcp-api-simple mcp-nginx-simple 2>/dev/null || true
docker rm mcp-api-simple mcp-nginx-simple 2>/dev/null || true

# Créer le répertoire de déploiement
echo "📁 Création du répertoire de déploiement..."
mkdir -p /tmp/mcp-deploy
cd /tmp/mcp-deploy

# Créer l'application FastAPI simple
echo "🐍 Création de l'application FastAPI..."
cat > app.py << 'PYTHON_EOF'
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from datetime import datetime

app = FastAPI(
    title="MCP API",
    description="API d'optimisation des nœuds Lightning Network",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StatusResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str

@app.get("/")
async def root():
    return {"message": "MCP API - Lightning Network Node Optimization"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mcp-api"
    }

@app.get("/api/v1/status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(
        status="operational",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        environment="production"
    )

@app.get("/api/v1/test")
async def test_endpoint():
    return {
        "message": "Test endpoint fonctionnel",
        "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
PYTHON_EOF

# Créer requirements.txt
echo "📦 Création des dépendances..."
cat > requirements.txt << 'REQ_EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
REQ_EOF

# Créer Dockerfile
echo "🐳 Création du Dockerfile..."
cat > Dockerfile << 'DOCKER_EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["python", "app.py"]
DOCKER_EOF

# Créer docker-compose.yml
echo "📋 Création du docker-compose.yml..."
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  api:
    build: .
    container_name: mcp-api-simple
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-sk-test-key}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: mcp-nginx-simple
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
    restart: unless-stopped
COMPOSE_EOF

# Créer configuration Nginx
echo "🌐 Création de la configuration Nginx..."
cat > nginx.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    upstream mcp_api {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://mcp_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /docs {
            proxy_pass http://mcp_api/docs;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /redoc {
            proxy_pass http://mcp_api/redoc;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
NGINX_EOF

# Construire et démarrer les services
echo "🔨 Construction des images Docker..."
docker-compose build

echo "🚀 Démarrage des services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 10

# Vérifier la santé des services
echo "🔍 Vérification de la santé des services..."

# Test API directe
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API directe (port 8000) - OK"
else
    echo "❌ API directe (port 8000) - ÉCHEC"
fi

# Test via Nginx
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ API via Nginx (port 80) - OK"
else
    echo "❌ API via Nginx (port 80) - ÉCHEC"
fi

# Test documentation
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ Documentation Swagger (port 8000) - OK"
else
    echo "❌ Documentation Swagger (port 8000) - ÉCHEC"
fi

echo ""
echo "🎉 Déploiement terminé !"
echo ""
echo "📋 URLs d'accès :"
echo "  • API directe: http://147.79.101.32:8000"
echo "  • Documentation Swagger: http://147.79.101.32:8000/docs"
echo "  • API via Nginx: http://147.79.101.32"
echo "  • Documentation via Nginx: http://147.79.101.32/docs"
echo "  • Health Check: http://147.79.101.32/health"
echo ""
echo "🔧 Commandes utiles :"
echo "  • Voir les logs: docker logs -f mcp-api-simple"
echo "  • Status: docker-compose ps"
echo "  • Arrêter: docker-compose down"
echo "  • Redémarrer: docker-compose restart"
echo ""

EOF

echo "✅ Déploiement terminé avec succès !" 