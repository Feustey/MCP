#!/bin/bash
# Script de nettoyage de la configuration Nginx
# À exécuter avant le déploiement SSL

set -e

echo "🧹 Nettoyage de la configuration Nginx..."

# Sauvegarde des configurations existantes
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Création d'une sauvegarde dans $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r /etc/nginx/* "$BACKUP_DIR/"

# Arrêt des services Coolify
echo "🛑 Arrêt des services Coolify..."
docker stop coolify coolify-proxy coolify-db coolify-realtime coolify-redis || true
docker rm coolify coolify-proxy coolify-db coolify-realtime coolify-redis || true

# Suppression des configurations existantes
echo "🗑️ Suppression des configurations existantes..."
rm -f /etc/nginx/sites-enabled/*
rm -f /etc/nginx/sites-available/*
rm -f /etc/nginx/conf.d/*

# Restauration de la configuration par défaut
echo "📝 Restauration de la configuration par défaut..."
cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
    multi_accept on;
}

http {
    ##
    # Basic Settings
    ##
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # MIME
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ##
    # SSL Settings
    ##
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    ##
    # Logging Settings
    ##
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    ##
    # Gzip Settings
    ##
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    ##
    # Virtual Host Configs
    ##
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF

# Création des répertoires nécessaires
echo "📁 Création des répertoires nécessaires..."
mkdir -p /var/www/mcp/static
chown -R www-data:www-data /var/www/mcp

# Test de la configuration
echo "🔍 Test de la configuration..."
nginx -t

# Redémarrage de Nginx
echo "🔄 Redémarrage de Nginx..."
systemctl restart nginx

echo "✅ Nettoyage terminé !"
echo "📋 Une sauvegarde de l'ancienne configuration a été créée dans $BACKUP_DIR" 