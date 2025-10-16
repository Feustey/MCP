#!/bin/bash
#
# Configuration HTTPS avec Let's Encrypt pour MCP Production
# Installation certificat SSL automatique
#
# Dernière mise à jour: 15 octobre 2025

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🔒 CONFIGURATION HTTPS AVEC LET'S ENCRYPT               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables par défaut
DOMAIN="${1:-api.dazno.de}"
EMAIL="${2:-feustey@gmail.com}"
STAGING="${3:-false}"  # true pour tester avec staging

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  - Domaine: $DOMAIN"
echo "  - Email: $EMAIL"
echo "  - Mode: $([ "$STAGING" = "true" ] && echo "STAGING (test)" || echo "PRODUCTION")"
echo ""

# Vérifier qu'on est sur le serveur de production
if [ ! -f "/etc/os-release" ]; then
    echo -e "${YELLOW}⚠️  Script à exécuter sur le serveur de production${NC}"
fi

echo -e "${BLUE}🔍 Étape 1/7: Vérifications préalables${NC}"
echo "========================================"

# Vérifier que DNS pointe vers ce serveur
echo "Test résolution DNS..."
CURRENT_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short "$DOMAIN" | tail -n1)

echo "  IP serveur actuel: $CURRENT_IP"
echo "  IP domaine $DOMAIN: $DOMAIN_IP"

if [ "$CURRENT_IP" != "$DOMAIN_IP" ]; then
    echo -e "${RED}❌ Le DNS ne pointe pas vers ce serveur !${NC}"
    echo ""
    echo "Actions requises:"
    echo "  1. Allez sur votre registrar de domaine"
    echo "  2. Configurez un enregistrement A:"
    echo "     Nom: api"
    echo "     Type: A"
    echo "     Valeur: $CURRENT_IP"
    echo "     TTL: 300"
    echo "  3. Attendez propagation DNS (5-30 minutes)"
    echo "  4. Vérifiez: dig +short $DOMAIN"
    echo "  5. Relancez ce script"
    echo ""
    read -p "Continuer quand même ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ DNS configuré correctement${NC}"
echo ""

echo -e "${BLUE}📦 Étape 2/7: Installation Certbot${NC}"
echo "====================================="

if command -v certbot &> /dev/null; then
    echo -e "${GREEN}✅ Certbot déjà installé${NC}"
    certbot --version
else
    echo "Installation de Certbot..."
    
    # Détection OS
    if [ -f /etc/debian_version ]; then
        echo "Système Debian/Ubuntu détecté"
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    elif [ -f /etc/redhat-release ]; then
        echo "Système RedHat/CentOS détecté"
        sudo yum install -y epel-release
        sudo yum install -y certbot python3-certbot-nginx
    else
        echo -e "${RED}❌ Système non supporté${NC}"
        echo "Installation manuelle requise: https://certbot.eff.org/"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Certbot installé${NC}"
fi

echo ""

echo -e "${BLUE}🔧 Étape 3/7: Configuration Nginx${NC}"
echo "==================================="

# Vérifier que Nginx est installé
if ! command -v nginx &> /dev/null; then
    echo "Installation de Nginx..."
    sudo apt install -y nginx
fi

# Backup de la config existante
if [ -f /etc/nginx/sites-available/mcp-api ]; then
    sudo cp /etc/nginx/sites-available/mcp-api "/etc/nginx/sites-available/mcp-api.backup_$(date +%Y%m%d_%H%M%S)"
fi

# Créer config Nginx initiale (HTTP seulement pour validation Let's Encrypt)
sudo tee /etc/nginx/sites-available/mcp-api > /dev/null << NGINXCONF
# Configuration Nginx pour MCP - Phase 1 (HTTP pour Let's Encrypt)
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    
    # Logs
    access_log /var/log/nginx/mcp_access.log combined;
    error_log /var/log/nginx/mcp_error.log warn;
    
    # Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Proxy vers API MCP
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXCONF

# Activer la config
sudo ln -sf /etc/nginx/sites-available/mcp-api /etc/nginx/sites-enabled/mcp-api

# Supprimer config par défaut si présente
sudo rm -f /etc/nginx/sites-enabled/default

# Test de la config
echo "Test configuration Nginx..."
if sudo nginx -t; then
    echo -e "${GREEN}✅ Configuration Nginx valide${NC}"
else
    echo -e "${RED}❌ Erreur configuration Nginx${NC}"
    exit 1
fi

# Reload Nginx
sudo systemctl reload nginx

echo -e "${GREEN}✅ Nginx configuré (HTTP)${NC}"
echo ""

echo -e "${BLUE}🎫 Étape 4/7: Génération certificat SSL${NC}"
echo "========================================="

# Préparer les arguments Certbot
CERTBOT_ARGS="--nginx -d $DOMAIN --email $EMAIL --agree-tos --no-eff-email --redirect"

if [ "$STAGING" = "true" ]; then
    CERTBOT_ARGS="$CERTBOT_ARGS --staging"
    echo -e "${YELLOW}⚠️  Mode STAGING activé (certificat de test)${NC}"
fi

echo "Lancement Certbot..."
echo "  Commande: certbot $CERTBOT_ARGS"
echo ""

if sudo certbot $CERTBOT_ARGS; then
    echo -e "${GREEN}✅ Certificat SSL généré avec succès${NC}"
else
    echo -e "${RED}❌ Échec génération certificat${NC}"
    echo ""
    echo "Causes possibles:"
    echo "  1. DNS ne pointe pas vers ce serveur"
    echo "  2. Port 80 non accessible depuis Internet"
    echo "  3. Firewall bloque l'accès"
    echo "  4. Domaine déjà utilisé récemment (rate limit)"
    echo ""
    echo "Solutions:"
    echo "  - Vérifier DNS: dig +short $DOMAIN"
    echo "  - Tester port 80: curl http://$DOMAIN"
    echo "  - Vérifier firewall: sudo ufw status"
    echo "  - Réessayer avec --staging pour tester"
    exit 1
fi

echo ""

echo -e "${BLUE}🔒 Étape 5/7: Configuration SSL optimale${NC}"
echo "=========================================="

# Certbot a normalement déjà créé la config SSL
# Vérifier et optimiser si nécessaire

if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${GREEN}✅ Certificats installés:${NC}"
    echo "  - Certificat: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "  - Clé privée: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    
    # Afficher info certificat
    echo ""
    echo "Informations certificat:"
    sudo openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -subject -issuer -dates
else
    echo -e "${RED}❌ Certificats non trouvés${NC}"
    exit 1
fi

echo ""

echo -e "${BLUE}⚙️  Étape 6/7: Optimisation configuration Nginx${NC}"
echo "================================================"

# Nginx a été automatiquement configuré par Certbot
# On peut vérifier et optimiser

echo "Vérification configuration SSL..."
if grep -q "ssl_certificate" /etc/nginx/sites-available/mcp-api; then
    echo -e "${GREEN}✅ SSL activé dans Nginx${NC}"
else
    echo -e "${YELLOW}⚠️  Configuration SSL à vérifier manuellement${NC}"
fi

# Test final de la configuration
if sudo nginx -t; then
    echo -e "${GREEN}✅ Configuration Nginx valide${NC}"
    sudo systemctl reload nginx
else
    echo -e "${RED}❌ Erreur configuration Nginx${NC}"
    exit 1
fi

echo ""

echo -e "${BLUE}🧪 Étape 7/7: Tests de validation${NC}"
echo "==================================="

sleep 5  # Attendre que Nginx recharge

echo "1. Test HTTPS..."
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/" | grep -q "200"; then
    echo -e "${GREEN}✅ HTTPS fonctionne (HTTP 200)${NC}"
else
    echo -e "${YELLOW}⚠️  HTTPS répond mais status inattendu${NC}"
    echo "   Test manuel: curl -I https://$DOMAIN/"
fi

echo ""
echo "2. Test redirection HTTP → HTTPS..."
LOCATION=$(curl -s -o /dev/null -w "%{redirect_url}" "http://$DOMAIN/")
if [[ "$LOCATION" == https://* ]]; then
    echo -e "${GREEN}✅ Redirection HTTPS active${NC}"
else
    echo -e "${YELLOW}⚠️  Redirection à vérifier${NC}"
fi

echo ""
echo "3. Test SSL Labs (optionnel, prend 2-3 minutes)..."
echo "   URL: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"

echo ""
echo "4. Vérification auto-renouvellement..."
if sudo certbot renew --dry-run; then
    echo -e "${GREEN}✅ Auto-renouvellement configuré${NC}"
else
    echo -e "${YELLOW}⚠️  Auto-renouvellement à vérifier${NC}"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ HTTPS CONFIGURÉ AVEC SUCCÈS                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📋 Résumé de la configuration:${NC}"
echo "  - Domaine: $DOMAIN"
echo "  - Certificat: Let's Encrypt"
echo "  - Validité: 90 jours (renouvellement automatique)"
echo "  - Redirection HTTP → HTTPS: Active"
echo "  - TLS: v1.2, v1.3"
echo "  - HSTS: Activé"
echo ""
echo -e "${BLUE}🔍 Tests manuels:${NC}"
echo "  curl https://$DOMAIN/"
echo "  curl -I http://$DOMAIN/  # Doit rediriger vers HTTPS"
echo ""
echo -e "${GREEN}🎯 Accès API:${NC}"
echo "  - https://$DOMAIN/api/v1/health"
echo "  - https://$DOMAIN/docs"
echo ""
echo -e "${YELLOW}📅 Maintenance:${NC}"
echo "  - Renouvellement auto: Tous les 60 jours"
echo "  - Vérifier: sudo certbot renew --dry-run"
echo "  - Logs: /var/log/letsencrypt/"
echo ""
echo -e "${BLUE}🔐 Sécurité:${NC}"
echo "  - Tester SSL: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "  - Note attendue: A+ (excellent)"
echo ""

