#!/bin/bash
# Script de déploiement via clé SSH temporaire pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

# Variables
DOMAIN="api.dazno.de"
ADMIN_EMAIL="admin@dazno.de"
SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"
SSH_KEY="/tmp/mcp_deploy_key"

echo "🚀 Déploiement pour $DOMAIN..."

# 1. Création de la clé SSH temporaire
echo "🔑 Création de la clé SSH temporaire..."
ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "mcp-deploy-key"

# 2. Copie de la clé publique sur le serveur
echo "📤 Copie de la clé publique..."
sshpass -p "$SSH_PASS" ssh-copy-id -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SERVER"

# 3. Création de la configuration Nginx
echo "📝 Création de la configuration Nginx..."
cat > /tmp/api.dazno.de.conf << 'EOF'
server {
    listen 80;
    server_name api.dazno.de;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name api.dazno.de;

    ssl_certificate /etc/letsencrypt/live/api.dazno.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dazno.de/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /docs {
        proxy_pass http://localhost:8000/docs;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# 4. Copie de la configuration sur le serveur
echo "📤 Copie de la configuration..."
scp -i "$SSH_KEY" /tmp/api.dazno.de.conf "$SSH_USER@$SERVER:/tmp/"

# 5. Installation et configuration sur le serveur
echo "🔧 Configuration du serveur..."
ssh -i "$SSH_KEY" "$SSH_USER@$SERVER" << 'ENDSSH'
# Mise à jour du système
echo "Feustey@AI!" | sudo -S apt-get update
echo "Feustey@AI!" | sudo -S apt-get install -y nginx certbot python3-certbot-nginx

# Configuration Nginx
echo "Feustey@AI!" | sudo -S mv /tmp/api.dazno.de.conf /etc/nginx/sites-available/
echo "Feustey@AI!" | sudo -S ln -sf /etc/nginx/sites-available/api.dazno.de.conf /etc/nginx/sites-enabled/
echo "Feustey@AI!" | sudo -S rm -f /etc/nginx/sites-enabled/default

# Test de la configuration
echo "Feustey@AI!" | sudo -S nginx -t

# Obtention du certificat SSL
echo "Feustey@AI!" | sudo -S certbot --nginx -d api.dazno.de --non-interactive --agree-tos -m admin@dazno.de

# Redémarrage de Nginx
echo "Feustey@AI!" | sudo -S systemctl restart nginx

# Configuration du pare-feu
echo "Feustey@AI!" | sudo -S ufw allow 'Nginx Full'
echo "Feustey@AI!" | sudo -S ufw allow ssh

# Vérification des services
echo "✅ État des services:"
echo "Feustey@AI!" | sudo -S systemctl status nginx | grep "active"
echo "Feustey@AI!" | sudo -S certbot certificates
ENDSSH

# 6. Nettoyage
echo "🧹 Nettoyage..."
rm -f "$SSH_KEY" "$SSH_KEY.pub" /tmp/api.dazno.de.conf
ssh -i "$SSH_KEY" "$SSH_USER@$SERVER" "rm -f ~/.ssh/authorized_keys"

echo "✅ Déploiement terminé"
echo ""
echo "📝 Points à vérifier:"
echo "  • Accès HTTPS: https://api.dazno.de"
echo "  • Documentation: https://api.dazno.de/docs"
echo "  • Santé API: https://api.dazno.de/health" 