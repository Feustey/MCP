#!/bin/bash
# deploy_remote_hostinger.sh
# Déploiement distant sur le serveur Hostinger en production

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Déploiement Distant - Production Hostinger          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration serveur distant (à adapter)
read -p "Entrez l'adresse du serveur Hostinger (ex: user@server.hostinger.com): " SERVER
if [ -z "$SERVER" ]; then
    echo -e "${RED}❌ Adresse serveur requise${NC}"
    exit 1
fi

read -p "Chemin distant du projet (défaut: ~/mcp): " REMOTE_PATH
REMOTE_PATH=${REMOTE_PATH:-~/mcp}

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Serveur: $SERVER"
echo "  Chemin: $REMOTE_PATH"
echo ""
read -p "Continuer? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo -e "${BLUE}═══ ÉTAPE 1/5: Test de connexion SSH ═══${NC}"
echo ""

if ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH OK'"; then
    echo -e "${GREEN}✓ Connexion SSH établie${NC}"
else
    echo -e "${RED}❌ Impossible de se connecter au serveur${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══ ÉTAPE 2/5: Vérification Docker distant ═══${NC}"
echo ""

if ssh "$SERVER" "docker ps > /dev/null 2>&1"; then
    echo -e "${GREEN}✓ Docker accessible sur le serveur${NC}"
else
    echo -e "${RED}❌ Docker non accessible sur le serveur${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══ ÉTAPE 3/5: Synchronisation des fichiers ═══${NC}"
echo ""

# Fichiers essentiels à synchroniser
FILES_TO_SYNC=(
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
)

echo -e "${YELLOW}Synchronisation des fichiers...${NC}"

# Créer le répertoire distant si nécessaire
ssh "$SERVER" "mkdir -p $REMOTE_PATH"

for item in "${FILES_TO_SYNC[@]}"; do
    if [ -e "$item" ]; then
        if [ -d "$item" ]; then
            echo "  • Sync dossier: $item"
            rsync -az --progress "$item" "$SERVER:$REMOTE_PATH/"
        else
            echo "  • Sync fichier: $item"
            rsync -az --progress "$item" "$SERVER:$REMOTE_PATH/"
        fi
    else
        echo -e "${YELLOW}  ⚠️  $item non trouvé (skip)${NC}"
    fi
done

echo -e "${GREEN}✓ Fichiers synchronisés${NC}"

echo ""
echo -e "${BLUE}═══ ÉTAPE 4/5: Déploiement sur le serveur ═══${NC}"
echo ""

# Exécuter le déploiement distant
ssh "$SERVER" "cd $REMOTE_PATH && bash -s" << 'ENDSSH'
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${YELLOW}Sur le serveur distant...${NC}"
echo ""

# Vérifier le fichier .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env non trouvé sur le serveur${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Fichier .env présent${NC}"

# Arrêter les services existants
echo -e "${YELLOW}Arrêt des services existants...${NC}"
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || echo "Aucun service à arrêter"

# Build de l'image
echo -e "${YELLOW}Build de l'image mcp-api...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache mcp-api

# Démarrage séquentiel des services
echo -e "${YELLOW}Démarrage de MongoDB...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mongodb
sleep 10

echo -e "${YELLOW}Démarrage de Redis...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d redis
sleep 5

echo -e "${YELLOW}Démarrage d'Ollama...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d ollama
sleep 15

echo -e "${YELLOW}Démarrage de l'API...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mcp-api
sleep 20

echo -e "${YELLOW}Démarrage de Nginx...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d nginx
sleep 5

echo ""
echo -e "${GREEN}✅ Services démarrés${NC}"
echo ""
docker-compose -f "$COMPOSE_FILE" ps
ENDSSH

echo -e "${GREEN}✓ Déploiement distant terminé${NC}"

echo ""
echo -e "${BLUE}═══ ÉTAPE 5/5: Vérification des services distants ═══${NC}"
echo ""

# Vérifier les services distants
ssh "$SERVER" "cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         DÉPLOIEMENT DISTANT TERMINÉ !                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Commandes de gestion à distance:${NC}"
echo ""
echo "  • Voir les logs:"
echo "    ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml logs -f'"
echo ""
echo "  • Redémarrer:"
echo "    ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml restart'"
echo ""
echo "  • Vérifier l'état:"
echo "    ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml ps'"
echo ""
echo "  • Arrêter:"
echo "    ssh $SERVER 'cd $REMOTE_PATH && docker-compose -f docker-compose.hostinger.yml down'"
echo ""

echo -e "${GREEN}✅ Déploiement distant réussi !${NC}"

