#!/bin/bash

# Script de déploiement avec retry pour SSH instable
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

HOSTINGER_USER="feustey"
HOSTINGER_HOST="147.79.101.32"
HOSTINGER_PATH="/home/feustey/unified-production"
MAX_RETRIES=5
RETRY_DELAY=10

echo -e "${BLUE}🚀 Déploiement Unifié Hostinger avec Retry${NC}"

# Fonction retry pour SSH
retry_ssh() {
    local cmd="$1"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        echo -e "${YELLOW}Tentative $attempt/$MAX_RETRIES...${NC}"
        
        if timeout 30 ssh -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 ${HOSTINGER_USER}@${HOSTINGER_HOST} "$cmd"; then
            echo -e "${GREEN}✅ Commande SSH réussie${NC}"
            return 0
        else
            echo -e "${RED}❌ Tentative $attempt échouée${NC}"
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo -e "${YELLOW}Attente de ${RETRY_DELAY}s avant retry...${NC}"
                sleep $RETRY_DELAY
            fi
            attempt=$((attempt + 1))
        fi
    done
    
    echo -e "${RED}❌ Toutes les tentatives SSH ont échoué${NC}"
    return 1
}

# Fonction retry pour SCP/rsync
retry_copy() {
    local src="$1"
    local dst="$2"
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        echo -e "${YELLOW}Copie - Tentative $attempt/$MAX_RETRIES...${NC}"
        
        if rsync -avz --timeout=30 --contimeout=10 "$src" "$dst"; then
            echo -e "${GREEN}✅ Copie réussie${NC}"
            return 0
        else
            echo -e "${RED}❌ Copie tentative $attempt échouée${NC}"
            if [ $attempt -lt $MAX_RETRIES ]; then
                sleep $RETRY_DELAY
            fi
            attempt=$((attempt + 1))
        fi
    done
    
    echo -e "${RED}❌ Toutes les tentatives de copie ont échoué${NC}"
    return 1
}

# 1. Créer les répertoires
echo -e "\n${BLUE}📁 Création des répertoires...${NC}"
retry_ssh "mkdir -p ${HOSTINGER_PATH}/{config/nginx,config/prometheus,mcp-data,t4g-data,logs/nginx,backups/mongo}"

# 2. Copier les fichiers de configuration
echo -e "\n${BLUE}📋 Copie des fichiers de configuration...${NC}"
retry_copy "docker-compose.hostinger-unified.yml" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/"
retry_copy "config/nginx/hostinger-unified.conf" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/config/nginx/"
retry_copy "config/nginx/nginx.conf" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/config/nginx/"
retry_copy "config/nginx/.htpasswd" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/config/nginx/"
retry_copy "config/prometheus/prometheus-unified.yml" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/config/prometheus/"
retry_copy ".env.unified-production" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/.env.production"

# 3. Arrêter les anciens services
echo -e "\n${BLUE}🛑 Arrêt des anciens services...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker stop \$(docker ps -aq --filter 'name=mcp' --filter 'name=t4g' --filter 'name=hostinger') 2>/dev/null || echo 'Aucun conteneur à arrêter'"

# 4. Nettoyer les anciens conteneurs
echo -e "\n${BLUE}🧹 Nettoyage...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker rm \$(docker ps -aq --filter 'name=mcp' --filter 'name=t4g' --filter 'name=hostinger') 2>/dev/null || echo 'Aucun conteneur à supprimer'"
retry_ssh "docker system prune -f"

# 5. Démarrer les nouveaux services
echo -e "\n${BLUE}🚀 Démarrage des services unifiés...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && export \$(cat .env.production | grep -v '^#' | xargs) && docker-compose -f docker-compose.hostinger-unified.yml up -d"

# 6. Attendre que les services démarrent
echo -e "\n${BLUE}⏳ Attente du démarrage des services...${NC}"
sleep 30

# 7. Vérifier le statut
echo -e "\n${BLUE}📊 Vérification du statut...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker-compose -f docker-compose.hostinger-unified.yml ps"

# 8. Afficher les logs
echo -e "\n${BLUE}📋 Logs des services...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker-compose -f docker-compose.hostinger-unified.yml logs --tail=20"

# 9. Configurer le firewall
echo -e "\n${BLUE}🔒 Configuration du firewall...${NC}"
retry_ssh "sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw deny 8000/tcp && sudo ufw deny 8001/tcp && sudo ufw reload" || echo "Firewall configuration skipped"

echo -e "\n${GREEN}🎉 Déploiement unifié terminé !${NC}"
echo -e "\n📊 ${BLUE}Services disponibles :${NC}"
echo -e "  • MCP API: https://api.dazno.de"
echo -e "  • Token-for-Good: https://token-for-good.com"
echo -e "  • Monitoring: http://147.79.101.32:8080"