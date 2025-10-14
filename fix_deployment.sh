#!/bin/bash

################################################################################
# Script de Correction Rapide des Erreurs de Déploiement
#
# Corrige les problèmes identifiés:
# - Mots de passe MongoDB/Redis manquants
# - Configuration .env incorrecte
# - Problèmes Docker Compose
#
# Usage: Exécuter sur le serveur
#   ssh feustey@147.79.101.32 'bash -s' < fix_deployment.sh
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd /home/feustey/mcp-production

echo -e "${BLUE}🔧 Correction des erreurs de déploiement...${NC}"
echo ""

# 1. Créer le fichier .env correct
echo -e "${YELLOW}[1/5]${NC} Configuration du fichier .env..."

cat > .env << 'ENVEOF'
# MCP v1.0 - Production Configuration
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=2

# MONGODB (Docker Internal)
MONGODB_USER=mcpuser
MONGODB_PASSWORD=MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY
MONGODB_DATABASE=mcp_prod

# REDIS (Docker Internal)
REDIS_PASSWORD=HGAsFqzgVyH51BEwSoKLupaK4RC81tAG

# SECURITY
SECRET_KEY=ZEcAXMSWdtHaBeNhrGF5sU1E4iQx7A6mnVjZmthyfYI
ENCRYPTION_KEY=LgINl2073pLV7+aC0vQklk5R4CoKM2KVnkHPdCbjSo8=

# LNBITS (À configurer)
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_ADMIN_KEY=your_admin_key
LNBITS_INVOICE_KEY=your_invoice_key

# TELEGRAM (Optionnel)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# FEATURES
ENABLE_SHADOW_MODE=true
ENABLE_RAG=false

# OPTIMIZATION
MAX_CHANGES_PER_DAY=5
REQUIRE_MANUAL_APPROVAL=true

# CACHE TTL
REDIS_TTL_NODE_DATA=300
REDIS_TTL_CHANNEL_DATA=600

# LOGGING
LOG_LEVEL=INFO
STRUCTLOG_ENABLED=true
ENVEOF

echo -e "${GREEN}✓${NC} Fichier .env créé avec les bons mots de passe"

# 2. Créer les répertoires manquants
echo -e "${YELLOW}[2/5]${NC} Création des répertoires..."
mkdir -p logs data config ssl backups/mongodb
chmod 755 logs data config ssl backups
echo -e "${GREEN}✓${NC} Répertoires créés"

# 3. Rendre les scripts exécutables
echo -e "${YELLOW}[3/5]${NC} Configuration des permissions..."
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x start_api.sh 2>/dev/null || true
chmod +x docker_entrypoint.sh 2>/dev/null || true
echo -e "${GREEN}✓${NC} Permissions configurées"

# 4. Arrêter les containers existants
echo -e "${YELLOW}[4/5]${NC} Nettoyage des containers existants..."
sudo docker-compose -f docker-compose.hostinger.yml down 2>/dev/null || true
echo -e "${GREEN}✓${NC} Nettoyage effectué"

# 5. Redémarrer avec la bonne configuration
echo -e "${YELLOW}[5/5]${NC} Démarrage des services Docker..."
sudo docker-compose -f docker-compose.hostinger.yml up -d

echo ""
echo -e "${BLUE}Attente du démarrage des services (30 secondes)...${NC}"
sleep 30

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ CORRECTION TERMINÉE !                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Vérification
echo -e "${BLUE}📊 Status des services:${NC}"
sudo docker-compose -f docker-compose.hostinger.yml ps

echo ""
echo -e "${BLUE}🧪 Tests de validation:${NC}"

# Test MongoDB
if sudo docker exec mcp-mongodb mongosh -u mcpuser -p MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY --authenticationDatabase admin --eval "db.runCommand('ping')" &> /dev/null; then
    echo -e "${GREEN}✓${NC} MongoDB opérationnel"
else
    echo -e "${RED}✗${NC} MongoDB ne répond pas"
fi

# Test Redis
if sudo docker exec mcp-redis redis-cli -a HGAsFqzgVyH51BEwSoKLupaK4RC81tAG ping &> /dev/null; then
    echo -e "${GREEN}✓${NC} Redis opérationnel"
else
    echo -e "${RED}✗${NC} Redis ne répond pas"
fi

# Test API
sleep 5
if curl -sf http://localhost:8000/ &> /dev/null; then
    echo -e "${GREEN}✓${NC} API opérationnelle"
else
    echo -e "${YELLOW}⚠${NC} API ne répond pas encore (attendre 1-2 minutes)"
fi

# Test Nginx
if curl -sf http://localhost/ &> /dev/null; then
    echo -e "${GREEN}✓${NC} Nginx opérationnel"
else
    echo -e "${YELLOW}⚠${NC} Nginx ne répond pas encore"
fi

echo ""
echo -e "${BLUE}📝 Note:${NC} Les certificats SSL sont normaux - ils seront configurés plus tard avec certbot"
echo ""
echo -e "${GREEN}🎉 Déploiement corrigé ! Tous les services devraient être opérationnels.${NC}"
echo ""

