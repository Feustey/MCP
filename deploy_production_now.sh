#!/bin/bash
# deploy_production_now.sh
# Déploiement guidé vers serveur de production Hostinger

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     DÉPLOIEMENT PRODUCTION - SERVEUR HOSTINGER          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "docker-compose.hostinger.yml" ]; then
    echo -e "${RED}❌ docker-compose.hostinger.yml non trouvé${NC}"
    echo "Exécutez ce script depuis le répertoire MCP"
    exit 1
fi

echo ""
echo -e "${BLUE}${BOLD}INFORMATIONS SERVEUR${NC}"
echo ""
echo -e "${YELLOW}Entrez les informations de connexion SSH :${NC}"
echo ""

# Demander l'adresse du serveur
read -p "$(echo -e ${CYAN}Adresse du serveur [user@host.hostinger.com]: ${NC})" SERVER_ADDRESS

if [ -z "$SERVER_ADDRESS" ]; then
    echo -e "${RED}❌ Adresse serveur requise${NC}"
    exit 1
fi

# Demander le chemin distant
read -p "$(echo -e ${CYAN}Chemin du projet sur le serveur [/root/mcp]: ${NC})" REMOTE_PATH
REMOTE_PATH=${REMOTE_PATH:-/root/mcp}

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  • Serveur : ${GREEN}$SERVER_ADDRESS${NC}"
echo "  • Chemin  : ${GREEN}$REMOTE_PATH${NC}"
echo ""
read -p "$(echo -e ${YELLOW}Confirmer et continuer? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Annulé${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 1/6: Test de connexion SSH ═══${NC}"
echo ""

if ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_ADDRESS" "echo 'Connexion SSH OK'" 2>/dev/null; then
    echo -e "${GREEN}✅ Connexion SSH établie${NC}"
else
    echo -e "${YELLOW}⚠️  Tentative avec authentification interactive...${NC}"
    if ssh -o ConnectTimeout=10 "$SERVER_ADDRESS" "echo 'Connexion SSH OK'"; then
        echo -e "${GREEN}✅ Connexion SSH établie${NC}"
    else
        echo -e "${RED}❌ Impossible de se connecter au serveur${NC}"
        echo ""
        echo -e "${YELLOW}Vérifiez:${NC}"
        echo "  1. L'adresse du serveur est correcte"
        echo "  2. Votre clé SSH est configurée : ssh-copy-id $SERVER_ADDRESS"
        echo "  3. Le serveur est accessible depuis votre réseau"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 2/6: Vérification Docker distant ═══${NC}"
echo ""

if ssh "$SERVER_ADDRESS" "docker --version" > /dev/null 2>&1; then
    DOCKER_VERSION=$(ssh "$SERVER_ADDRESS" "docker --version")
    echo -e "${GREEN}✅ Docker installé sur le serveur${NC}"
    echo "   $DOCKER_VERSION"
else
    echo -e "${RED}❌ Docker non trouvé sur le serveur${NC}"
    echo ""
    echo -e "${YELLOW}Docker doit être installé sur le serveur. Voulez-vous que je vous guide?${NC}"
    read -p "Afficher les commandes d'installation Docker? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Connectez-vous au serveur et exécutez:"
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  systemctl enable docker"
        echo "  systemctl start docker"
    fi
    exit 1
fi

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 3/6: Préparation du répertoire distant ═══${NC}"
echo ""

echo -e "${YELLOW}Création du répertoire sur le serveur...${NC}"
ssh "$SERVER_ADDRESS" "mkdir -p $REMOTE_PATH"
echo -e "${GREEN}✅ Répertoire $REMOTE_PATH créé${NC}"

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 4/6: Synchronisation des fichiers ═══${NC}"
echo ""

# Liste des fichiers/dossiers à synchroniser
SYNC_ITEMS=(
    "docker-compose.hostinger.yml"
    "Dockerfile.production"
    "nginx-docker.conf"
    "mongo-init.js"
    ".env"
    "scripts/"
    "app/"
    "src/"
    "config/"
    "rag/"
    "requirements.txt"
)

echo -e "${YELLOW}Synchronisation en cours...${NC}"
echo ""

for item in "${SYNC_ITEMS[@]}"; do
    if [ -e "$item" ]; then
        echo -e "  📤 ${CYAN}$item${NC}"
        if [ -d "$item" ]; then
            rsync -az --progress "$item" "$SERVER_ADDRESS:$REMOTE_PATH/" 2>&1 | grep -E "^(sending|sent)" || true
        else
            rsync -az --progress "$item" "$SERVER_ADDRESS:$REMOTE_PATH/" 2>&1 | grep -E "^(sending|sent)" || true
        fi
    else
        echo -e "  ${YELLOW}⚠️  $item non trouvé (skip)${NC}"
    fi
done

echo ""
echo -e "${GREEN}✅ Fichiers synchronisés${NC}"

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 5/6: Déploiement sur le serveur ═══${NC}"
echo ""

echo -e "${YELLOW}Exécution du déploiement distant...${NC}"
echo ""

# Script de déploiement à exécuter sur le serveur
ssh "$SERVER_ADDRESS" "cd $REMOTE_PATH && bash -s" << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${BLUE}Sur le serveur de production...${NC}"
echo ""

# Vérifier .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé${NC}"
    echo "Vérifiez que le fichier .env a été synchronisé"
    exit 1
fi
echo -e "${GREEN}✓ Fichier .env présent${NC}"

# Arrêter les services existants
echo -e "${YELLOW}Arrêt des services existants...${NC}"
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || echo "Aucun service à arrêter"

# Build de l'image
echo ""
echo -e "${YELLOW}Build de l'image mcp-api (peut prendre 5-10 min)...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache mcp-api

# Démarrage séquentiel
echo ""
echo -e "${YELLOW}Démarrage de MongoDB...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mongodb
sleep 10

echo -e "${YELLOW}Démarrage de Redis...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d redis
sleep 5

echo -e "${YELLOW}Démarrage d'Ollama...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d ollama
sleep 15

echo -e "${YELLOW}Démarrage de l'API MCP...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mcp-api
sleep 20

echo -e "${YELLOW}Démarrage de Nginx...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d nginx
sleep 5

echo ""
echo -e "${GREEN}✅ Tous les services démarrés${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" ps
ENDSSH

echo ""
echo -e "${GREEN}✅ Déploiement distant terminé${NC}"

echo ""
echo -e "${BLUE}${BOLD}═══ PHASE 6/6: Vérification des services ═══${NC}"
echo ""

echo -e "${YELLOW}État des conteneurs sur le serveur :${NC}"
echo ""
ssh "$SERVER_ADDRESS" "cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps"

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
echo -e "${BLUE}${BOLD}COMMANDES UTILES${NC}"
echo ""
echo -e "${CYAN}Voir les logs :${NC}"
echo "  ssh $SERVER_ADDRESS 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml logs -f'"
echo ""
echo -e "${CYAN}Vérifier l'état :${NC}"
echo "  ssh $SERVER_ADDRESS 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps'"
echo ""
echo -e "${CYAN}Redémarrer :${NC}"
echo "  ssh $SERVER_ADDRESS 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml restart'"
echo ""
echo -e "${CYAN}Arrêter :${NC}"
echo "  ssh $SERVER_ADDRESS 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml down'"
echo ""

echo -e "${GREEN}${BOLD}🎉 Le système MCP est maintenant déployé en production sur Hostinger !${NC}"
echo ""

