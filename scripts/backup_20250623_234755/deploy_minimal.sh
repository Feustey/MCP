#!/bin/bash

# Script de déploiement minimal pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

# Variables
DOMAIN="api.dazno.de"
ADMIN_EMAIL="admin@dazno.de"
SERVER_IP="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

# Installation de sshpass si nécessaire
if ! command -v sshpass &> /dev/null; then
    echo "🔧 Installation de sshpass..."
    brew install sshpass
fi

echo "🚀 Déploiement minimal pour $DOMAIN..."

# Création de la configuration Nginx
cat > nginx.conf << 'EOF'
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

# Copie de la configuration sur le serveur
echo "📤 Copie de la configuration sur le serveur..."
sshpass -p "$SSH_PASS" scp nginx.conf $SSH_USER@$SERVER_IP:/tmp/api.dazno.de.conf

# Commandes à exécuter sur le serveur
echo "🔧 Configuration du serveur..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP << 'ENDSSH'
# Installation des dépendances
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configuration Nginx
sudo mv /tmp/api.dazno.de.conf /etc/nginx/sites-available/api.dazno.de.conf
sudo ln -sf /etc/nginx/sites-available/api.dazno.de.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test de la configuration
sudo nginx -t

# Obtention du certificat SSL
sudo certbot --nginx -d api.dazno.de --non-interactive --agree-tos -m admin@dazno.de

# Redémarrage de Nginx
sudo systemctl restart nginx

# Vérification des services
echo "✅ État des services:"
sudo systemctl status nginx | grep "active"
sudo certbot certificates
ENDSSH

# Nettoyage local
rm nginx.conf

echo "✅ Déploiement terminé"
echo ""
echo "📝 Points à vérifier:"
echo "  • Accès HTTPS: https://api.dazno.de"
echo "  • Documentation: https://api.dazno.de/docs"
echo "  • Santé API: https://api.dazno.de/health" 