#!/bin/bash
# scripts/check_hostinger_services.sh
# Vérification rapide de l'état des services en production Hostinger

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Vérification Services Production Hostinger          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Services attendus
SERVICES=("mcp-mongodb" "mcp-redis" "mcp-api" "mcp-nginx" "mcp-ollama")

echo -e "${YELLOW}🔍 Vérification de l'état des conteneurs...${NC}"
echo ""

RUNNING=0
STOPPED=0

for service in "${SERVICES[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        STATUS=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null)
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "no healthcheck")
        
        if [ "$STATUS" = "running" ]; then
            if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "no healthcheck" ]; then
                echo -e "${GREEN}✅ $service${NC} - Running ($HEALTH)"
                RUNNING=$((RUNNING + 1))
            else
                echo -e "${YELLOW}⚠️  $service${NC} - Running mais $HEALTH"
                RUNNING=$((RUNNING + 1))
            fi
        else
            echo -e "${RED}❌ $service${NC} - Arrêté"
            STOPPED=$((STOPPED + 1))
        fi
    else
        echo -e "${RED}❌ $service${NC} - Non trouvé"
        STOPPED=$((STOPPED + 1))
    fi
done

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "Services actifs: ${GREEN}$RUNNING${NC} / ${YELLOW}$((RUNNING + STOPPED))${NC}"
echo -e "Services arrêtés: ${RED}$STOPPED${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Afficher les logs des services en erreur
if [ $STOPPED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Services en erreur détectés${NC}"
    echo ""
    echo -e "${BLUE}Commandes de diagnostic:${NC}"
    echo "  • Voir l'état: docker-compose -f $COMPOSE_FILE ps"
    echo "  • Voir les logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  • Redémarrer: docker-compose -f $COMPOSE_FILE restart"
    echo ""
fi

# Vérifier les ports
echo -e "${YELLOW}🔌 Vérification des ports...${NC}"
echo ""

PORTS=("8000:mcp-api" "80:nginx" "443:nginx" "11434:ollama")

for port_mapping in "${PORTS[@]}"; do
    PORT=$(echo $port_mapping | cut -d: -f1)
    SERVICE=$(echo $port_mapping | cut -d: -f2)
    
    if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
        echo -e "${GREEN}✅ Port $PORT${NC} - Ouvert ($SERVICE)"
    else
        echo -e "${RED}❌ Port $PORT${NC} - Fermé ($SERVICE)"
    fi
done

echo ""

# Test de santé de l'API
echo -e "${YELLOW}🏥 Test de santé de l'API...${NC}"
echo ""

if curl -sf http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API accessible${NC} - http://localhost:8000/"
    
    # Test du temps de réponse
    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/ 2>/dev/null || echo "999")
    if (( $(echo "$RESPONSE_TIME < 2" | bc -l 2>/dev/null || echo "0") )); then
        echo -e "${GREEN}   Temps de réponse: ${RESPONSE_TIME}s${NC}"
    else
        echo -e "${YELLOW}   Temps de réponse: ${RESPONSE_TIME}s (lent)${NC}"
    fi
else
    echo -e "${RED}❌ API non accessible${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

if [ $STOPPED -eq 0 ]; then
    echo -e "${GREEN}✅ Tous les services sont opérationnels !${NC}"
    exit 0
else
    echo -e "${RED}⚠️  $STOPPED service(s) nécessite(nt) une intervention${NC}"
    exit 1
fi

