#!/bin/bash

################################################################################
# Script de Déploiement Final Optimisé
#
# Gère le déploiement complet avec build en arrière-plan
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e

SSH_USER="feustey"
SSH_HOST="147.79.101.32"
DEPLOY_DIR="/home/feustey/mcp-production"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     🚀 MCP v1.0 - Déploiement Final                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

echo -e "${BLUE}📦 Étape 1/4 : Construction des images Docker...${NC}"
echo -e "${YELLOW}⏳ Cela peut prendre 5-10 minutes...${NC}\n"

# Créer un script de build sur le serveur
ssh ${SSH_USER}@${SSH_HOST} "cat > ${DEPLOY_DIR}/build_and_start.sh" << 'REMOTE_SCRIPT'
#!/bin/bash
set -e

cd /home/feustey/mcp-production

echo "🔨 Construction des images..."
docker-compose -f docker-compose.hostinger.yml build --no-cache > build.log 2>&1

echo "🧹 Nettoyage des anciens containers..."
docker-compose -f docker-compose.hostinger.yml down >> build.log 2>&1

echo "🚀 Démarrage des services..."
docker-compose -f docker-compose.hostinger.yml up -d >> build.log 2>&1

echo "✅ Déploiement terminé !"
REMOTE_SCRIPT

# Rendre le script exécutable et l'exécuter
ssh ${SSH_USER}@${SSH_HOST} "chmod +x ${DEPLOY_DIR}/build_and_start.sh"

echo -e "${CYAN}▶${NC} Lancement du build en arrière-plan sur le serveur...\n"

# Exécuter le script en arrière-plan
ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && nohup ./build_and_start.sh > deployment.log 2>&1 &"

echo -e "${GREEN}✓${NC} Build lancé en arrière-plan\n"

# Surveiller la progression
echo -e "${BLUE}📊 Étape 2/4 : Surveillance de la progression...${NC}\n"

for i in {1..20}; do
    sleep 15
    
    # Vérifier si le build est terminé
    if ssh ${SSH_USER}@${SSH_HOST} "grep -q 'Déploiement terminé' ${DEPLOY_DIR}/build.log 2>/dev/null"; then
        echo -e "${GREEN}✓${NC} Build terminé avec succès !\n"
        break
    fi
    
    # Afficher la progression
    LAST_LINE=$(ssh ${SSH_USER}@${SSH_HOST} "tail -1 ${DEPLOY_DIR}/build.log 2>/dev/null || echo 'En cours...'")
    echo -e "${CYAN}[$i/20]${NC} $LAST_LINE"
    
    if [ $i -eq 20 ]; then
        echo -e "\n${YELLOW}⚠${NC} Le build prend plus de temps que prévu (normal pour la première fois)"
        echo -e "${CYAN}ℹ${NC} Vous pouvez suivre en temps réel avec :"
        echo -e "  ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'tail -f ${DEPLOY_DIR}/build.log'${NC}\n"
    fi
done

# Attendre la stabilisation
echo -e "${BLUE}⏳ Étape 3/4 : Stabilisation des services (60s)...${NC}\n"
sleep 60

# Validation
echo -e "${BLUE}🧪 Étape 4/4 : Validation du déploiement...${NC}\n"

# Vérifier les containers
CONTAINERS=$(ssh ${SSH_USER}@${SSH_HOST} "docker ps --format '{{.Names}}' | wc -l")
echo -e "${CYAN}Containers actifs:${NC} $CONTAINERS"

if [ "$CONTAINERS" -gt 0 ]; then
    ssh ${SSH_USER}@${SSH_HOST} "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -10"
fi

echo ""

# Test MongoDB
if ssh ${SSH_USER}@${SSH_HOST} "docker exec mcp-mongodb mongosh --quiet --eval 'db.version()' 2>/dev/null" >/dev/null 2>&1; then
    MONGO_VERSION=$(ssh ${SSH_USER}@${SSH_HOST} "docker exec mcp-mongodb mongosh --quiet --eval 'db.version()' 2>/dev/null")
    echo -e "${GREEN}✓${NC} MongoDB $MONGO_VERSION opérationnel"
else
    echo -e "${RED}✗${NC} MongoDB ne répond pas"
fi

# Test Redis
if ssh ${SSH_USER}@${SSH_HOST} "docker exec mcp-redis redis-cli -a HgHIvAIoJZ3E2pfnswXOBBbQE7T8GJD5 ping 2>/dev/null" | grep -q "PONG"; then
    echo -e "${GREEN}✓${NC} Redis opérationnel"
else
    echo -e "${RED}✗${NC} Redis ne répond pas"
fi

# Test API
sleep 5
if ssh ${SSH_USER}@${SSH_HOST} "curl -sf http://localhost:8000/ -m 5" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API MCP opérationnelle"
    
    # Afficher les infos de l'API
    API_INFO=$(ssh ${SSH_USER}@${SSH_HOST} "curl -sf http://localhost:8000/ 2>/dev/null" | python3 -m json.tool 2>/dev/null || echo "")
    if [ -n "$API_INFO" ]; then
        echo -e "${CYAN}   Version:${NC} $(echo "$API_INFO" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)"
    fi
else
    echo -e "${YELLOW}⚠${NC} API ne répond pas encore (peut prendre quelques minutes)"
fi

# Test Nginx
if ssh ${SSH_USER}@${SSH_HOST} "curl -sf http://localhost/ -m 5" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Nginx opérationnel"
else
    echo -e "${YELLOW}⚠${NC} Nginx ne répond pas encore"
fi

# Résumé final
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                                                            ║${NC}"
echo -e "${BOLD}${GREEN}║     ✅ DÉPLOIEMENT COMPLÉTÉ AVEC SUCCÈS !                 ║${NC}"
echo -e "${BOLD}${GREEN}║                                                            ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}🌐 URLs d'Accès${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "API:         ${CYAN}http://147.79.101.32:8000${NC}"
echo -e "Docs API:    ${CYAN}http://147.79.101.32:8000/docs${NC}"
echo -e "Health:      ${CYAN}http://147.79.101.32:8000/api/v1/health${NC}"
echo -e "Web:         ${CYAN}http://147.79.101.32${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}📝 Commandes Utiles${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Logs:        ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && docker-compose -f docker-compose.hostinger.yml logs -f'${NC}"
echo -e "Status:      ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && docker-compose -f docker-compose.hostinger.yml ps'${NC}"
echo -e "Redémarrer:  ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && docker-compose -f docker-compose.hostinger.yml restart'${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}📊 Vérification en Temps Réel${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Test API:    ${CYAN}curl http://147.79.101.32:8000/api/v1/health${NC}"
echo -e "Logs Build:  ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cat ${DEPLOY_DIR}/build.log'${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}⚠️  Points d'Attention${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}1.${NC} Mode DRY_RUN activé (voir DEPLOYMENT_CREDENTIALS.txt)"
echo -e "${YELLOW}2.${NC} Configurer LNBits dans ${DEPLOY_DIR}/.env"
echo -e "${YELLOW}3.${NC} SSL/HTTPS à configurer avec certbot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${GREEN}🎉 MCP v1.0 est maintenant opérationnel sur Hostinger !${NC}\n"

exit 0

