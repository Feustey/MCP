#!/bin/bash
# Script de déploiement SSL complet pour api.dazno.de
# À exécuter sur le serveur de production

set -e

APP_DIR="/var/www/mcp"
DOMAIN="api.dazno.de"

echo "🔄 Arrêt des services Coolify..."
docker stop coolify coolify-proxy coolify-db coolify-realtime coolify-redis || true
docker rm coolify coolify-proxy coolify-db coolify-realtime coolify-redis || true

echo "🧹 Nettoyage des configurations Nginx..."
rm -f /etc/nginx/sites-enabled/*
rm -f /etc/nginx/conf.d/*

echo "📦 Installation de Certbot..."
apt-get update > /dev/null 2>&1
apt-get install -y certbot python3-certbot-nginx > /dev/null 2>&1

echo "🔒 Vérification/Obtention du certificat SSL..."
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "✅ Le certificat SSL existe déjà pour $DOMAIN"
    certbot renew --nginx --non-interactive
else
    echo "🔄 Obtention d'un nouveau certificat SSL..."
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email contact@dazno.de \
        --domains $DOMAIN \
        --preferred-challenges http
fi

echo "🔄 Configuration de Nginx..."

# Configuration du site
cat > /etc/nginx/conf.d/$DOMAIN.conf << 'EOF'
# Configuration HTTP
server {
    listen 80;
    server_name api.dazno.de;
    return 301 https://$server_name$request_uri;
}

# Configuration HTTPS
server {
    listen 443 ssl http2;
    server_name api.dazno.de;

    # Configuration SSL
    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Configuration de sécurité SSL moderne
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (uncomment if you're sure)
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Configuration de sécurité supplémentaire
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Configuration des logs
    access_log /var/log/nginx/api.dazno.de.access.log combined buffer=512k flush=1m;
    error_log /var/log/nginx/api.dazno.de.error.log warn;

    # Configuration du proxy
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

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer size
        proxy_buffer_size 16k;
        proxy_buffers 8 16k;
        proxy_busy_buffers_size 32k;

        # Gestion des erreurs
        proxy_intercept_errors on;
        error_page 500 502 503 504 /50x.html;
    }

    # Page d'erreur personnalisée
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }

    # Configuration des fichiers statiques
    location /static/ {
        alias /var/www/mcp/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Configuration de la documentation
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header Cache-Control "no-store";
        expires 0;
    }

    # Configuration de la santé
    location /health {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header Cache-Control "no-store";
        expires 0;
    }

    # Configuration pour Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/lib/letsencrypt/;
    }
}
EOF

echo "🔍 Test de la configuration Nginx..."
nginx -t

echo "🔄 Redémarrage de Nginx..."
systemctl restart nginx

echo "🔄 Redémarrage des services MCP..."
cd $APP_DIR && docker-compose up -d

echo "✅ Déploiement SSL terminé !"
echo "📋 Vérifiez https://$DOMAIN dans votre navigateur"

# Vérification finale
echo "🔍 Vérification du certificat..."
curl -I https://api.dazno.de 