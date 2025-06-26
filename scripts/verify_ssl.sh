#!/bin/bash
# Script de vérification SSL pour api.dazno.de
# À exécuter après le déploiement SSL

set -e

DOMAIN="api.dazno.de"
APP_DIR="/var/www/mcp"

echo "🔍 Vérification du déploiement SSL pour $DOMAIN..."

# Vérification du certificat SSL
echo -n "📜 Certificat SSL : "
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "✅ Présent"
    echo "   Détails du certificat :"
    certbot certificates | grep -A 6 "$DOMAIN"
else
    echo "❌ Manquant"
    exit 1
fi

# Vérification de la configuration Nginx
echo -n "🔧 Configuration Nginx : "
if nginx -t > /dev/null 2>&1; then
    echo "✅ Valide"
else
    echo "❌ Invalide"
    nginx -t
    exit 1
fi

# Vérification du service Nginx
echo -n "🚀 Service Nginx : "
if systemctl is-active --quiet nginx; then
    echo "✅ En cours d'exécution"
else
    echo "❌ Arrêté"
    exit 1
fi

# Vérification des ports
echo -n "🔌 Ports (80/443) : "
if netstat -tuln | grep -q ":80 " && netstat -tuln | grep -q ":443 "; then
    echo "✅ En écoute"
else
    echo "❌ Non disponibles"
    netstat -tuln | grep -E ":80 |:443 "
    exit 1
fi

# Vérification des services Docker
echo "🐳 Services Docker :"
cd $APP_DIR
if [ -f "docker-compose.yml" ]; then
    docker-compose ps
else
    echo "❌ docker-compose.yml non trouvé dans $APP_DIR"
    exit 1
fi

# Test HTTPS
echo -n "🌐 Test HTTPS : "
if curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health; then
    echo "✅ Accessible"
else
    echo "❌ Non accessible"
    echo "   Détails de l'erreur :"
    curl -v https://$DOMAIN/health 2>&1
    exit 1
fi

echo "✅ Vérification SSL terminée avec succès !" 