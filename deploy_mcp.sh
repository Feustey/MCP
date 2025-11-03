#!/bin/bash
# deploy_mcp.sh
# Script de déploiement intelligent MCP - Gère local et distant

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.hostinger.yml"

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║           MCP - Déploiement Production                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 1: Diagnostic de l'environnement
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}═══ DIAGNOSTIC DE L'ENVIRONNEMENT ═══${NC}"
echo ""

# Vérifier Docker
if ! docker ps > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker n'est pas accessible${NC}"
    echo ""
    echo -e "${CYAN}Voulez-vous démarrer Docker Desktop ? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        ./scripts/check_docker.sh
    else
        echo -e "${RED}❌ Docker est requis pour le déploiement local${NC}"
        echo ""
        echo -e "${CYAN}Options disponibles :${NC}"
        echo "  1. Démarrer Docker et relancer ce script"
        echo "  2. Utiliser le déploiement distant : ./deploy_remote_hostinger.sh"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Docker accessible${NC}"

# Vérifier les conteneurs existants
EXISTING_CONTAINERS=$(docker ps -a --filter "name=mcp-" --format "{{.Names}}" | wc -l)
RUNNING_CONTAINERS=$(docker ps --filter "name=mcp-" --format "{{.Names}}" | wc -l)

if [ "$EXISTING_CONTAINERS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Conteneurs existants détectés: $EXISTING_CONTAINERS${NC}"
    echo -e "${YELLOW}   Conteneurs actifs: $RUNNING_CONTAINERS${NC}"
fi

# Vérifier si le port 8000 est utilisé
PORT_8000_USED=$(lsof -i :8000 2>/dev/null | grep LISTEN | wc -l)
if [ "$PORT_8000_USED" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Port 8000 déjà utilisé${NC}"
    lsof -i :8000 2>/dev/null | grep LISTEN | head -5
    echo ""
    echo -e "${CYAN}Le port 8000 est utilisé par un processus Python (probablement une instance de dev)${NC}"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 2: Choix du mode de déploiement
# ═══════════════════════════════════════════════════════════════════════
echo -e "${BLUE}${BOLD}═══ CHOIX DU MODE DE DÉPLOIEMENT ═══${NC}"
echo ""

echo -e "${CYAN}Que voulez-vous faire ?${NC}"
echo ""
echo "  1) ${GREEN}Redémarrer les conteneurs existants${NC} (rapide - 1 min)"
echo "  2) ${YELLOW}Déploiement complet local${NC} (rebuild - 15-20 min)"
echo "  3) ${BLUE}Déploiement distant (Hostinger)${NC} (rsync + deploy - 10-15 min)"
echo "  4) ${CYAN}Vérifier l'état uniquement${NC}"
echo "  5) ${RED}Annuler${NC}"
echo ""
read -p "Votre choix (1-5): " CHOICE

case $CHOICE in
    1)
        # ═════════════════════════════════════════════════════════
        # OPTION 1: Redémarrage rapide
        # ═════════════════════════════════════════════════════════
        echo ""
        echo -e "${BLUE}${BOLD}═══ REDÉMARRAGE DES CONTENEURS ═══${NC}"
        echo ""
        
        if [ "$EXISTING_CONTAINERS" -eq 0 ]; then
            echo -e "${RED}❌ Aucun conteneur existant trouvé${NC}"
            echo "Utilisez l'option 2 pour un déploiement complet"
            exit 1
        fi
        
        # Arrêter le process Python si nécessaire
        if [ "$PORT_8000_USED" -gt 0 ]; then
            echo -e "${YELLOW}⚠️  Un processus utilise le port 8000${NC}"
            echo -e "${CYAN}Voulez-vous l'arrêter ? (y/N)${NC}"
            read -r response
            if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
                PID=$(lsof -ti :8000 2>/dev/null)
                if [ -n "$PID" ]; then
                    kill -9 $PID
                    echo -e "${GREEN}✓ Processus arrêté${NC}"
                    sleep 2
                fi
            fi
        fi
        
        echo -e "${YELLOW}Redémarrage des conteneurs...${NC}"
        docker-compose -f "$COMPOSE_FILE" restart
        
        echo ""
        echo -e "${YELLOW}⏳ Attente de la stabilisation (15s)...${NC}"
        sleep 15
        
        echo ""
        ./scripts/check_hostinger_services.sh || true
        ;;
        
    2)
        # ═════════════════════════════════════════════════════════
        # OPTION 2: Déploiement complet local
        # ═════════════════════════════════════════════════════════
        echo ""
        echo -e "${BLUE}${BOLD}═══ DÉPLOIEMENT COMPLET LOCAL ═══${NC}"
        echo ""
        
        # Arrêter le process Python si nécessaire
        if [ "$PORT_8000_USED" -gt 0 ]; then
            echo -e "${YELLOW}⚠️  Un processus utilise le port 8000${NC}"
            echo -e "${CYAN}Il doit être arrêté pour continuer. Arrêter ? (y/N)${NC}"
            read -r response
            if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
                PID=$(lsof -ti :8000 2>/dev/null)
                if [ -n "$PID" ]; then
                    kill -9 $PID
                    echo -e "${GREEN}✓ Processus arrêté${NC}"
                    sleep 2
                fi
            else
                echo -e "${RED}❌ Le port 8000 doit être libéré${NC}"
                exit 1
            fi
        fi
        
        echo -e "${YELLOW}Lancement du déploiement complet...${NC}"
        echo ""
        ./deploy_hostinger_production.sh
        ;;
        
    3)
        # ═════════════════════════════════════════════════════════
        # OPTION 3: Déploiement distant
        # ═════════════════════════════════════════════════════════
        echo ""
        echo -e "${BLUE}${BOLD}═══ DÉPLOIEMENT DISTANT ═══${NC}"
        echo ""
        
        echo -e "${YELLOW}Lancement du déploiement sur Hostinger...${NC}"
        echo ""
        ./deploy_remote_hostinger.sh
        ;;
        
    4)
        # ═════════════════════════════════════════════════════════
        # OPTION 4: Vérification uniquement
        # ═════════════════════════════════════════════════════════
        echo ""
        echo -e "${BLUE}${BOLD}═══ VÉRIFICATION DE L'ÉTAT ═══${NC}"
        echo ""
        
        ./scripts/check_hostinger_services.sh || true
        
        echo ""
        echo -e "${CYAN}Conteneurs Docker :${NC}"
        docker ps -a --filter "name=mcp-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        if [ "$PORT_8000_USED" -gt 0 ]; then
            echo ""
            echo -e "${CYAN}Processus Python sur port 8000 :${NC}"
            lsof -i :8000 2>/dev/null | grep LISTEN
        fi
        ;;
        
    5)
        echo ""
        echo -e "${YELLOW}Annulé${NC}"
        exit 0
        ;;
        
    *)
        echo ""
        echo -e "${RED}❌ Choix invalide${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}${BOLD}✅ Opération terminée !${NC}"
echo ""

