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
