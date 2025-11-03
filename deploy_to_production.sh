#!/bin/bash
# deploy_to_production.sh
# Déploiement automatisé sur serveur Hostinger

set -e

# Configuration
SERVER="feustey@147.79.101.32"
REMOTE_PATH="/home/feustey/mcp"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     DÉPLOIEMENT AUTOMATISÉ - SERVEUR HOSTINGER          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${BLUE}📊 Configuration:${NC}"
echo "  • Serveur: ${GREEN}$SERVER${NC}"
echo "  • Chemin: ${GREEN}$REMOTE_PATH${NC}"
echo ""

# PHASE 1: Test connexion SSH
echo -e "${BLUE}═══ PHASE 1/6: Test de connexion SSH ═══${NC}"
echo ""

if ssh -o ConnectTimeout=10 "$SERVER" "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connexion SSH établie${NC}"
else
    echo -e "${RED}❌ Impossible de se connecter au serveur${NC}"
    exit 1
fi

# PHASE 2: Vérification Docker
echo ""
echo -e "${BLUE}═══ PHASE 2/6: Vérification Docker distant ═══${NC}"
echo ""

DOCKER_VERSION=$(ssh "$SERVER" "docker --version" 2>/dev/null || echo "not found")
if [[ "$DOCKER_VERSION" == *"not found"* ]]; then
    echo -e "${RED}❌ Docker non installé sur le serveur${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker installé: $DOCKER_VERSION${NC}"

# PHASE 3: Création du répertoire
echo ""
echo -e "${BLUE}═══ PHASE 3/6: Préparation du répertoire distant ═══${NC}"
echo ""

ssh "$SERVER" "mkdir -p $REMOTE_PATH"
echo -e "${GREEN}✅ Répertoire créé: $REMOTE_PATH${NC}"

# PHASE 4: Synchronisation des fichiers
echo ""
echo -e "${BLUE}═══ PHASE 4/6: Synchronisation des fichiers ═══${NC}"
echo ""

FILES_TO_SYNC=(
    "docker-compose.hostinger.yml"
    "Dockerfile.production"
    "nginx-docker.conf"
    "mongo-init.js"
    ".env"
    "requirements.txt"
)

DIRS_TO_SYNC=(
    "app"
    "src"
    "config"
    "rag"
    "scripts"
)

echo -e "${YELLOW}Synchronisation des fichiers...${NC}"
for file in "${FILES_TO_SYNC[@]}"; do
    if [ -f "$file" ]; then
        echo "  📄 $file"
        rsync -az "$file" "$SERVER:$REMOTE_PATH/" || echo "    ⚠️  Erreur (continué)"
    fi
done

echo ""
echo -e "${YELLOW}Synchronisation des répertoires...${NC}"
for dir in "${DIRS_TO_SYNC[@]}"; do
    if [ -d "$dir" ]; then
        echo "  📁 $dir/"
        rsync -az "$dir/" "$SERVER:$REMOTE_PATH/$dir/" || echo "    ⚠️  Erreur (continué)"
    fi
done

echo ""
echo -e "${GREEN}✅ Fichiers synchronisés${NC}"

# PHASE 5: Déploiement sur le serveur
echo ""
echo -e "${BLUE}═══ PHASE 5/6: Déploiement sur le serveur ═══${NC}"
echo ""

echo -e "${YELLOW}Exécution du script de déploiement distant...${NC}"
echo ""

ssh "$SERVER" "cd $REMOTE_PATH && bash -s" << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${YELLOW}⚙️  Arrêt des services existants...${NC}"
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || echo "Aucun service à arrêter"

echo ""
echo -e "${YELLOW}🔨 Build de l'image Docker (5-10 min)...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache mcp-api

echo ""
echo -e "${YELLOW}🗄️  Démarrage de MongoDB...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mongodb
sleep 10

echo -e "${YELLOW}💾 Démarrage de Redis...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d redis
sleep 5

echo -e "${YELLOW}🤖 Démarrage d'Ollama...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d ollama
sleep 15

echo -e "${YELLOW}🚀 Démarrage de l'API MCP...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mcp-api
sleep 20

echo -e "${YELLOW}🌐 Démarrage de Nginx...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d nginx
sleep 5

echo ""
echo -e "${GREEN}✅ Tous les services démarrés${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" ps
ENDSSH

echo ""
echo -e "${GREEN}✅ Déploiement distant terminé${NC}"

# PHASE 6: Vérification
echo ""
echo -e "${BLUE}═══ PHASE 6/6: Vérification des services ═══${NC}"
echo ""

echo -e "${YELLOW}État des conteneurs sur le serveur:${NC}"
echo ""
ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps"

echo ""
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     ✅ DÉPLOIEMENT PRODUCTION TERMINÉ !                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${BLUE}🎯 COMMANDES UTILES${NC}"
echo ""
echo -e "${CYAN}Voir les logs:${NC}"
echo "  ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml logs -f'"
echo ""
echo -e "${CYAN}Vérifier l'état:${NC}"
echo "  ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps'"
echo ""
echo -e "${CYAN}Redémarrer:${NC}"
echo "  ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml restart'"
echo ""
echo -e "${CYAN}Tester l'API:${NC}"
echo "  curl http://147.79.101.32:8000/health"
echo ""

echo -e "${GREEN}🎉 Le système MCP est maintenant déployé en production sur Hostinger !${NC}"
echo ""
