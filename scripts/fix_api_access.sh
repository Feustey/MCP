#!/bin/bash

# Script pour diagnostiquer et corriger l'accès aux APIs
set -e

HOST="feustey@147.79.101.32"
REMOTE_PATH="/home/feustey/mcp-production"

echo "🔧 DIAGNOSTIC ET CORRECTION DES APIs HOSTINGER"
echo "=============================================="

# Fonction pour exécuter des commandes avec retry
exec_remote() {
    local cmd="$1"
    local desc="$2"
    echo "⚡ $desc"
    ssh -o ConnectTimeout=20 -o ServerAliveInterval=5 "$HOST" "$cmd" || echo "❌ Erreur: $desc"
}

# 1. Vérifier l'état des conteneurs
exec_remote "cd $REMOTE_PATH && docker ps -a" "État des conteneurs Docker"

# 2. Vérifier les logs nginx
exec_remote "cd $REMOTE_PATH && docker logs hostinger-nginx 2>&1 | tail -20" "Logs Nginx"

# 3. Vérifier les logs MCP API
exec_remote "cd $REMOTE_PATH && docker logs mcp-api 2>&1 | tail -20" "Logs MCP API"

# 4. Vérifier le processus nginx sur l'hôte
exec_remote "ps aux | grep nginx | head -5" "Processus nginx hôte"

# 5. Vérifier les ports en écoute
exec_remote "ss -tlnp | grep -E ':(80|443|8000)'" "Ports en écoute"

# 6. Arrêter et redémarrer proprement
echo "🔄 Redémarrage des services..."
exec_remote "cd $REMOTE_PATH && docker-compose -f docker-compose.production-complete.yml down" "Arrêt des services"

# 7. Nettoyer
exec_remote "docker system prune -f" "Nettoyage Docker"

# 8. Créer une configuration nginx simple
cat > /tmp/nginx_simple.conf << 'EOF'
server {
    listen 80;
    server_name api.dazno.de;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name token-for-good.com;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 9. Copier la config simple
scp /tmp/nginx_simple.conf "$HOST:$REMOTE_PATH/nginx_simple.conf"

# 10. Docker compose simplifié
cat > /tmp/docker-compose-simple.yml << 'EOF'
version: '3.8'

services:
  mcp-api:
    image: feustey/dazno:latest
    container_name: mcp-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - HOST=0.0.0.0
      - PORT=8000
      - MONGO_URL=mongodb+srv://feustey:sIiEp8oiB2hjYBbi@dazia.pin4fwl.mongodb.net/mcp?retryWrites=true&w=majority&appName=Dazia
      - REDIS_URL=redis://default:EqbM5xJAkh9gvdOyVoYiWR9EoHRBXcjY@redis-16818.crce202.eu-west-3-1.ec2.redns.redis-cloud.com:16818/0

  nginx:
    image: nginx:alpine
    container_name: nginx-simple
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx_simple.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - mcp-api
EOF

# 11. Copier le compose simple
scp /tmp/docker-compose-simple.yml "$HOST:$REMOTE_PATH/"

# 12. Démarrer avec la config simple
exec_remote "cd $REMOTE_PATH && docker-compose -f docker-compose-simple.yml up -d" "Démarrage simple"

# 13. Attendre
echo "⏳ Attente 30s pour le démarrage..."
sleep 30

# 14. Vérifier les conteneurs
exec_remote "cd $REMOTE_PATH && docker ps" "Vérification conteneurs"

# 15. Test direct
echo "🧪 Test des endpoints..."
curl -m 10 -I http://147.79.101.32/ || echo "❌ HTTP direct échoué"
curl -m 10 -I http://api.dazno.de/ || echo "❌ api.dazno.de échoué"

echo "✅ Diagnostic et correction terminés"