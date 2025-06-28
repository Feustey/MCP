#!/bin/bash
set -e

# Script de préparation pour déploiement Coolify
# Dernière mise à jour: 7 janvier 2025

echo "🚀 Préparation du déploiement Coolify pour MCP"

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Vérification de l'état Git
echo -e "${YELLOW}📋 Vérification de l'état Git...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Des modifications non commitées détectées${NC}"
    git status
    read -p "Voulez-vous commiter ces modifications ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "feat: préparation déploiement Coolify - $(date)"
    fi
fi

# Vérification de la branche
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}✅ Branche actuelle: $CURRENT_BRANCH${NC}"

# Push vers le repository distant
echo -e "${YELLOW}📤 Push vers le repository distant...${NC}"
git push origin $CURRENT_BRANCH

# Affichage des informations pour Coolify
echo -e "${GREEN}✅ Préparation terminée !${NC}"
echo ""
echo -e "${GREEN}📋 Paramètres pour Coolify:${NC}"
echo "Repository: $(git remote get-url origin)"
echo "Branche: $CURRENT_BRANCH"
echo "Docker Compose File: docker-compose.coolify.yml"
echo "Dockerfile: Dockerfile.coolify"
echo "Port: 8000"
echo "Health Check: /health"
echo ""
echo -e "${GREEN}🔧 Variables d'environnement à configurer dans Coolify:${NC}"
echo "- SECURITY_SECRET_KEY"
echo "- OPENAI_API_KEY"
echo "- AI_OPENAI_API_KEY"
echo "- REDIS_PASSWORD"
echo "- LNBITS_URL"
echo "- LNBITS_ADMIN_KEY"
echo "- LNBITS_INVOICE_KEY"
echo "- AMBOSS_API_KEY"
echo "- TELEGRAM_BOT_TOKEN (optionnel)"
echo "- TELEGRAM_CHAT_ID (optionnel)"
echo ""
echo -e "${GREEN}🔌 URLs de connexion:${NC}"
echo "MongoDB: mongodb://147.79.101.32:27017/mcp"
echo "Redis: redis://147.79.101.32:6379/0"
echo "API: https://api.dazno.de" 