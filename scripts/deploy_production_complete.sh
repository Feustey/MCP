#!/bin/bash

# ============================================
# Déploiement Production Complet MCP + RAG
# Hostinger avec tous les endpoints
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

HOSTINGER_USER="feustey"
HOSTINGER_HOST="147.79.101.32"
HOSTINGER_PATH="/home/feustey/mcp-production"

echo -e "${BLUE}🚀 DÉPLOIEMENT PRODUCTION COMPLET${NC}"
echo -e "${BLUE}   MCP API + RAG + Token-for-Good${NC}"
echo -e "${BLUE}   Tous les endpoints activés${NC}"
echo -e "${BLUE}===============================================${NC}"

# Fonction pour retry SSH
retry_ssh() {
    local cmd="$1"
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${YELLOW}SSH Tentative $attempt/$max_attempts...${NC}"
        if ssh -o ConnectTimeout=30 -o ServerAliveInterval=10 ${HOSTINGER_USER}@${HOSTINGER_HOST} "$cmd"; then
            return 0
        fi
        attempt=$((attempt + 1))
        [ $attempt -le $max_attempts ] && sleep 15
    done
    return 1
}

# Fonction pour copier avec retry
retry_copy() {
    local src="$1"
    local dst="$2"
    local attempt=1
    local max_attempts=3
    
    while [ $attempt -le $max_attempts ]; do
        echo -e "${YELLOW}Copie tentative $attempt/$max_attempts: $(basename $src)${NC}"
        if rsync -avz --timeout=60 "$src" "$dst"; then
            return 0
        fi
        attempt=$((attempt + 1))
        [ $attempt -le $max_attempts ] && sleep 10
    done
    return 1
}

# 1. Vérifier les prérequis locaux
echo -e "\n${BLUE}📋 Vérification des prérequis...${NC}"
required_files=(
    "docker-compose.production-complete.yml"
    "config/nginx/hostinger-unified.conf"
    "config/qdrant/config.yaml"
    "config/ollama/modelfile"
    ".env.unified-production"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Fichier manquant: $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ Tous les fichiers requis sont présents${NC}"

# 2. Créer la structure sur le serveur
echo -e "\n${BLUE}🏗️  Création de la structure sur le serveur...${NC}"
retry_ssh "mkdir -p ${HOSTINGER_PATH}/{config/{nginx,qdrant,ollama,prometheus,grafana/{provisioning,dashboards}},mcp-data/{logs,data,rag,backups,reports},t4g-data/{logs,uploads,data},logs/nginx,scripts}"

# 3. Copier les fichiers de configuration
echo -e "\n${BLUE}📁 Copie des fichiers de configuration...${NC}"
retry_copy "docker-compose.production-complete.yml" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/"
retry_copy "config/" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/"
retry_copy ".env.unified-production" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/.env.production"
retry_copy "scripts/" "${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/"

# 4. Arrêter les anciens services
echo -e "\n${BLUE}🛑 Arrêt des anciens services...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker-compose down --remove-orphans || true"

# 5. Nettoyer l'environnement
echo -e "\n${BLUE}🧹 Nettoyage de l'environnement...${NC}"
retry_ssh "docker system prune -f"

# 6. Démarrer les services
echo -e "\n${BLUE}🚀 Démarrage de tous les services...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && export \$(cat .env.production | grep -v '^#' | xargs) && docker-compose -f docker-compose.production-complete.yml up -d"

# 7. Attendre le démarrage
echo -e "\n${BLUE}⏳ Attente du démarrage complet...${NC}"
sleep 90

# 8. Vérifier le statut
echo -e "\n${BLUE}📊 Vérification du statut...${NC}"
retry_ssh "cd ${HOSTINGER_PATH} && docker-compose -f docker-compose.production-complete.yml ps"

# 9. Tests des endpoints
echo -e "\n${BLUE}🧪 Test des endpoints...${NC}"
sleep 30

if curl -s -f https://api.dazno.de/health >/dev/null; then
    echo -e "${GREEN}✅ MCP API: OK${NC}"
else
    echo -e "${YELLOW}⏳ MCP API: En attente...${NC}"
fi

# 10. Résumé final
echo -e "\n${GREEN}🎉 DÉPLOIEMENT COMPLET TERMINÉ !${NC}"
echo -e "\n📊 Services disponibles :"
echo -e "  • MCP API: https://api.dazno.de"
echo -e "  • Documentation: https://api.dazno.de/docs"
echo -e "  • RAG: https://api.dazno.de/api/v1/rag/"
echo -e "  • Token-for-Good: https://token-for-good.com"
echo -e "  • Monitoring: http://147.79.101.32:8080/grafana"