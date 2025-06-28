#!/bin/bash

# Script de déploiement complet pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

set -e  # Arrêt en cas d'erreur

# Variables
DOMAIN="api.dazno.de"
ADMIN_EMAIL="admin@dazno.de"
SERVER_IP="147.79.101.32"
DEPLOY_PATH="/tmp/mcp-deploy"
NGINX_CONF="/etc/nginx"
SSL_PATH="/etc/letsencrypt/live/$DOMAIN"

echo "🚀 Déploiement de MCP sur $DOMAIN..."

# Connexion SSH et exécution du déploiement
ssh -t feustey@$SERVER_IP << 'EOF'

# 1. Préparation de l'environnement
echo "📦 Préparation de l'environnement..."
sudo mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH

# 2. Installation des dépendances
echo "🔧 Installation des dépendances..."
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 3. Configuration de Nginx
echo "🌐 Configuration de Nginx..."
sudo cat > /tmp/api.dazno.de.conf << 'NGINX_CONF'
server {
    listen 80;
    server_name api.dazno.de;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name api.dazno.de;

    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' 'https://app.dazno.de' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;
    }

    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        access_log off;
        add_header Content-Type application/json;
    }
}
NGINX_CONF

sudo mv /tmp/api.dazno.de.conf /etc/nginx/sites-available/api.dazno.de.conf
sudo ln -sf /etc/nginx/sites-available/api.dazno.de.conf /etc/nginx/sites-enabled/

# 4. Test de la configuration Nginx
echo "🔍 Test de la configuration Nginx..."
sudo nginx -t

# 5. Obtention du certificat SSL
echo "🔒 Obtention du certificat SSL..."
sudo certbot --nginx -d api.dazno.de --non-interactive --agree-tos -m admin@dazno.de

# 6. Redémarrage de Nginx
echo "🔄 Redémarrage de Nginx..."
sudo systemctl restart nginx

# 7. Configuration du pare-feu
echo "🛡️ Configuration du pare-feu..."
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh

# 8. Test de la configuration
echo "🔍 Test de la configuration..."
curl -k https://localhost/health

# 9. Vérification des services
echo "✅ Vérification des services..."
sudo systemctl status nginx | grep "active"
sudo certbot certificates

echo "🎉 Déploiement terminé!"
echo "📝 Points à vérifier:"
echo "  • Accès HTTPS: https://api.dazno.de"
echo "  • Documentation: https://api.dazno.de/docs"
echo "  • Santé API: https://api.dazno.de/health"
echo "  • CORS avec app.dazno.de"
echo "  • Certificats SSL"

EOF

echo "✅ Script de déploiement terminé" 