#!/bin/bash
# deploy_hostinger_production.sh
# Déploiement complet de tous les services sur Hostinger

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Déploiement Production Hostinger - Complet          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 0: Vérifications préalables
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 0/7: Vérifications préalables ═══${NC}"
echo ""

# Vérifier .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env non trouvé${NC}"
    echo "Copier env.hostinger.example vers .env et le configurer"
    exit 1
fi
echo -e "${GREEN}✓ Fichier .env trouvé${NC}"

# Vérifier docker-compose
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ Fichier $COMPOSE_FILE non trouvé${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Fichier $COMPOSE_FILE trouvé${NC}"

# Vérifier Docker
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker n'est pas accessible${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker accessible${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 1: Arrêt des services existants
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 1/7: Arrêt des services existants ═══${NC}"
echo ""

if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${YELLOW}Arrêt des services en cours...${NC}"
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✓ Services arrêtés${NC}"
else
    echo -e "${YELLOW}Aucun service en cours d'exécution${NC}"
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 2: Build des images
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 2/7: Build des images Docker ═══${NC}"
echo ""

echo -e "${YELLOW}Build de l'image mcp-api (peut prendre 5-10 min)...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache mcp-api
echo -e "${GREEN}✓ Image mcp-api buildée${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 3: Démarrage des services de base
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 3/7: Démarrage des services de base ═══${NC}"
echo ""

echo -e "${YELLOW}Démarrage de MongoDB...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mongodb
sleep 10

if docker ps | grep -q "mcp-mongodb"; then
    echo -e "${GREEN}✓ MongoDB démarré${NC}"
else
    echo -e "${RED}❌ Échec du démarrage de MongoDB${NC}"
    docker-compose -f "$COMPOSE_FILE" logs mongodb
    exit 1
fi

echo -e "${YELLOW}Démarrage de Redis...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d redis
sleep 5

if docker ps | grep -q "mcp-redis"; then
    echo -e "${GREEN}✓ Redis démarré${NC}"
else
    echo -e "${RED}❌ Échec du démarrage de Redis${NC}"
    docker-compose -f "$COMPOSE_FILE" logs redis
    exit 1
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 4: Démarrage d'Ollama
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 4/7: Démarrage d'Ollama ═══${NC}"
echo ""

echo -e "${YELLOW}Démarrage d'Ollama...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d ollama
sleep 15

if docker ps | grep -q "mcp-ollama"; then
    echo -e "${GREEN}✓ Ollama démarré${NC}"
else
    echo -e "${RED}❌ Échec du démarrage d'Ollama${NC}"
    docker-compose -f "$COMPOSE_FILE" logs ollama
    exit 1
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 5: Téléchargement des modèles Ollama
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 5/7: Téléchargement des modèles Ollama ═══${NC}"
echo ""

if [ -f "scripts/pull_lightweight_models.sh" ]; then
    echo -e "${YELLOW}Téléchargement des modèles ultra-légers...${NC}"
    bash scripts/pull_lightweight_models.sh
    echo -e "${GREEN}✓ Modèles téléchargés${NC}"
else
    echo -e "${YELLOW}⚠️  Script de téléchargement des modèles non trouvé${NC}"
    echo "Les modèles seront téléchargés manuellement plus tard"
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 6: Démarrage de l'API et Nginx
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 6/7: Démarrage de l'API et Nginx ═══${NC}"
echo ""

echo -e "${YELLOW}Démarrage de l'API MCP...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d mcp-api
sleep 20

if docker ps | grep -q "mcp-api"; then
    echo -e "${GREEN}✓ API MCP démarrée${NC}"
else
    echo -e "${RED}❌ Échec du démarrage de l'API${NC}"
    docker-compose -f "$COMPOSE_FILE" logs mcp-api
    exit 1
fi

echo -e "${YELLOW}Démarrage de Nginx...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d nginx
sleep 5

if docker ps | grep -q "mcp-nginx"; then
    echo -e "${GREEN}✓ Nginx démarré${NC}"
else
    echo -e "${RED}❌ Échec du démarrage de Nginx${NC}"
    docker-compose -f "$COMPOSE_FILE" logs nginx
    exit 1
fi
echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 7: Validation du déploiement
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}═══ ÉTAPE 7/7: Validation du déploiement ═══${NC}"
echo ""

echo -e "${YELLOW}⏳ Attente de la stabilisation (30s)...${NC}"
sleep 30

# Vérifier tous les services
echo -e "${YELLOW}Vérification de l'état des services...${NC}"
echo ""

if [ -f "scripts/check_hostinger_services.sh" ]; then
    bash scripts/check_hostinger_services.sh
else
    docker-compose -f "$COMPOSE_FILE" ps
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              DÉPLOIEMENT TERMINÉ !                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Services déployés:${NC}"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo -e "${BLUE}Accès aux services:${NC}"
echo "  • API MCP: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Nginx HTTP: http://localhost:80"
echo "  • Nginx HTTPS: https://localhost:443"
echo "  • Ollama: http://localhost:11434"
echo ""

echo -e "${BLUE}Commandes utiles:${NC}"
echo "  • Logs API:      docker-compose -f $COMPOSE_FILE logs -f mcp-api"
echo "  • Logs Ollama:   docker-compose -f $COMPOSE_FILE logs -f ollama"
echo "  • Logs Nginx:    docker-compose -f $COMPOSE_FILE logs -f nginx"
echo "  • Arrêter tout:  docker-compose -f $COMPOSE_FILE down"
echo "  • Vérification:  ./scripts/check_hostinger_services.sh"
echo ""

echo -e "${GREEN}✅ Déploiement Production Hostinger réussi !${NC}"
echo ""

