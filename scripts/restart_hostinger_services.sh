#!/bin/bash
# scripts/restart_hostinger_services.sh
# Redémarrage rapide de tous les services

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Redémarrage Services Production Hostinger        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Option: redémarrer un service spécifique ou tous
if [ -n "$1" ]; then
    SERVICE="$1"
    echo -e "${YELLOW}Redémarrage du service: $SERVICE${NC}"
    docker-compose -f "$COMPOSE_FILE" restart "$SERVICE"
    echo -e "${GREEN}✓ Service $SERVICE redémarré${NC}"
else
    echo -e "${YELLOW}Redémarrage de tous les services...${NC}"
    docker-compose -f "$COMPOSE_FILE" restart
    echo -e "${GREEN}✓ Tous les services redémarrés${NC}"
fi

echo ""
echo -e "${YELLOW}⏳ Attente de la stabilisation (10s)...${NC}"
sleep 10

echo ""
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo -e "${GREEN}✅ Redémarrage terminé !${NC}"

