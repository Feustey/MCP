#!/bin/bash

# Script de déploiement final pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

# Variables
DOMAIN="api.dazno.de"
ADMIN_EMAIL="admin@dazno.de"
SERVER_IP="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

echo "🚀 Déploiement final pour $DOMAIN..."

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

# Création du script d'installation sur le serveur
cat > install.sh << 'EOF'
#!/bin/bash

# Mise à jour du système
echo "$SSH_PASS" | sudo -S apt-get update
echo "$SSH_PASS" | sudo -S apt-get install -y nginx certbot python3-certbot-nginx

# Configuration Nginx
echo "$SSH_PASS" | sudo -S mv /tmp/api.dazno.de.conf /etc/nginx/sites-available/api.dazno.de.conf
echo "$SSH_PASS" | sudo -S ln -sf /etc/nginx/sites-available/api.dazno.de.conf /etc/nginx/sites-enabled/
echo "$SSH_PASS" | sudo -S rm -f /etc/nginx/sites-enabled/default

# Test de la configuration
echo "$SSH_PASS" | sudo -S nginx -t

# Obtention du certificat SSL
echo "$SSH_PASS" | sudo -S certbot --nginx -d api.dazno.de --non-interactive --agree-tos -m admin@dazno.de

# Redémarrage de Nginx
echo "$SSH_PASS" | sudo -S systemctl restart nginx

# Configuration du pare-feu
echo "$SSH_PASS" | sudo -S ufw allow 'Nginx Full'
echo "$SSH_PASS" | sudo -S ufw allow ssh

# Vérification des services
echo "✅ État des services:"
echo "$SSH_PASS" | sudo -S systemctl status nginx | grep "active"
echo "$SSH_PASS" | sudo -S certbot certificates
EOF

# Rendre le script exécutable
chmod +x install.sh

# Copie des fichiers sur le serveur
echo "📤 Copie des fichiers sur le serveur..."
sshpass -p "$SSH_PASS" scp nginx.conf $SSH_USER@$SERVER_IP:/tmp/api.dazno.de.conf
sshpass -p "$SSH_PASS" scp install.sh $SSH_USER@$SERVER_IP:/tmp/install.sh

# Exécution du script d'installation
echo "🔧 Exécution du script d'installation..."
sshpass -p "$SSH_PASS" ssh -t $SSH_USER@$SERVER_IP "cd /tmp && chmod +x install.sh && ./install.sh"

# Nettoyage local
rm nginx.conf install.sh

echo "✅ Déploiement terminé"
echo ""
echo "📝 Points à vérifier:"
echo "  • Accès HTTPS: https://api.dazno.de"
echo "  • Documentation: https://api.dazno.de/docs"
echo "  • Santé API: https://api.dazno.de/health" 