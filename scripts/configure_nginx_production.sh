#!/bin/bash
#
# Configuration Nginx pour MCP Production
# Proxy HTTPS vers l'API sur localhost:8000
#
# Dernière mise à jour: 10 octobre 2025
# Requiert: Accès sudo

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  🌐 CONFIGURATION NGINX POUR MCP PRODUCTION           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Vérifier si on a sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  Ce script requiert les privilèges sudo"
    echo "Exécution: sudo $0"
    exit 1
fi

echo "✍️  Étape 1/5: Création de la configuration nginx"
echo "=================================================="

# Créer le fichier de configuration
sudo tee /etc/nginx/sites-available/mcp-api > /dev/null << 'NGINXCONF'
# Configuration Nginx pour MCP Lightning API
# Dernière mise à jour: 10 octobre 2025

upstream mcp_backend {
    server 127.0.0.1:8000 fail_timeout=30s max_fails=3;
    keepalive 32;
}

# Redirection HTTP -> HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name api.dazno.de dazno.de www.dazno.de;
    
    # Rediriger tout le trafic HTTP vers HTTPS
    return 301 https://$server_name$request_uri;
}

# Configuration HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.dazno.de dazno.de www.dazno.de;

    # Logs
    access_log /var/log/nginx/mcp_access.log combined;
    error_log /var/log/nginx/mcp_error.log warn;

    # SSL Configuration (Let's Encrypt)
    # À adapter selon vos certificats
    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;
    
    # Paramètres SSL optimisés
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Client settings
    client_max_body_size 10M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Proxy vers l'API MCP
    location / {
        proxy_pass http://mcp_backend;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        
        # WebSocket support (si nécessaire)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check (monitoring)
    location = /health {
        proxy_pass http://mcp_backend/;
        access_log off;
    }

    # Documentation Swagger
    location /docs {
        proxy_pass http://mcp_backend/docs;
        proxy_set_header Host $host;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://mcp_backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
NGINXCONF

echo "✅ Configuration nginx créée: /etc/nginx/sites-available/mcp-api"
echo ""

echo "🔗 Étape 2/5: Activation de la configuration"
echo "============================================="

# Créer le lien symbolique
sudo ln -sf /etc/nginx/sites-available/mcp-api /etc/nginx/sites-enabled/mcp-api

# Supprimer la config par défaut si elle existe
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "🗑️  Suppression de la config par défaut..."
    sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "✅ Configuration activée"
echo ""

echo "🧪 Étape 3/5: Test de la configuration"
echo "======================================="

if sudo nginx -t; then
    echo "✅ Configuration nginx valide"
else
    echo "❌ Erreur dans la configuration nginx"
    echo "Vérifier manuellement: sudo nginx -t"
    exit 1
fi

echo ""
echo "🔄 Étape 4/5: Reload nginx"
echo "=========================="

if sudo systemctl reload nginx; then
    echo "✅ Nginx rechargé avec succès"
else
    echo "⚠️  Erreur lors du reload, tentative de restart..."
    sudo systemctl restart nginx
fi

echo ""
echo "⏳ Attente 5 secondes..."
sleep 5

echo ""
echo "✅ Étape 5/5: Tests de validation"
echo "=================================="

echo ""
echo "1. Test local HTTP:"
curl -s http://localhost/ | head -3 || echo "⚠️  HTTP non accessible"

echo ""
echo "2. Test via domaine (si SSL configuré):"
curl -k -s https://api.dazno.de/ | head -3 || echo "ℹ️  HTTPS non encore configuré (normal sans certificat)"

echo ""
echo "3. Test API directe:"
curl -s http://localhost:8000/ | head -3

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ NGINX CONFIGURÉ AVEC SUCCÈS                       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Prochaines étapes:"
echo "  1. Si vous n'avez pas de certificat SSL, installez Let's Encrypt:"
echo "     sudo apt install certbot python3-certbot-nginx"
echo "     sudo certbot --nginx -d api.dazno.de"
echo ""
echo "  2. Vérifier l'accès:"
echo "     curl https://api.dazno.de/"
echo ""
echo "  3. Configurer systemd (script suivant):"
echo "     sudo ./scripts/configure_systemd_autostart.sh"

