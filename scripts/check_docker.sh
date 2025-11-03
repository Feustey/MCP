#!/bin/bash
# scripts/check_docker.sh
# Vérifier et démarrer Docker si nécessaire

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Vérification Docker Desktop                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier si Docker est accessible
if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker est accessible et en cours d'exécution${NC}"
    echo ""
    docker version --format '{{.Server.Version}}' | xargs -I {} echo "  Version Docker: {}"
    echo ""
    exit 0
fi

echo -e "${YELLOW}⚠️  Docker daemon non accessible${NC}"
echo ""

# Détecter l'OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}Système détecté: macOS${NC}"
    echo ""
    
    # Vérifier si Docker Desktop est installé
    if [ -d "/Applications/Docker.app" ]; then
        echo -e "${GREEN}✓ Docker Desktop est installé${NC}"
        echo ""
        echo -e "${YELLOW}Tentative de démarrage de Docker Desktop...${NC}"
        open -a Docker
        
        echo -e "${YELLOW}⏳ Attente du démarrage de Docker (peut prendre 30-60 secondes)...${NC}"
        
        # Attendre que Docker soit prêt (max 120 secondes)
        COUNTER=0
        MAX_WAIT=120
        
        while [ $COUNTER -lt $MAX_WAIT ]; do
            if docker ps > /dev/null 2>&1; then
                echo ""
                echo -e "${GREEN}✅ Docker est maintenant accessible !${NC}"
                echo ""
                docker version --format '{{.Server.Version}}' | xargs -I {} echo "  Version Docker: {}"
                echo ""
                exit 0
            fi
            
            sleep 5
            COUNTER=$((COUNTER + 5))
            echo -n "."
        done
        
        echo ""
        echo -e "${RED}❌ Docker ne répond toujours pas après ${MAX_WAIT} secondes${NC}"
        echo ""
        echo -e "${YELLOW}Actions suggérées:${NC}"
        echo "  1. Vérifier que Docker Desktop est bien lancé dans la barre de menu"
        echo "  2. Redémarrer Docker Desktop manuellement"
        echo "  3. Vérifier les logs: ~/Library/Containers/com.docker.docker/Data/log/"
        exit 1
    else
        echo -e "${RED}❌ Docker Desktop n'est pas installé${NC}"
        echo ""
        echo -e "${YELLOW}Pour installer Docker Desktop:${NC}"
        echo "  1. Télécharger: https://www.docker.com/products/docker-desktop"
        echo "  2. Installer l'application"
        echo "  3. Lancer Docker Desktop"
        echo "  4. Relancer ce script"
        exit 1
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${BLUE}Système détecté: Linux${NC}"
    echo ""
    
    # Vérifier si Docker est installé
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker est installé${NC}"
        echo ""
        echo -e "${YELLOW}Tentative de démarrage du service Docker...${NC}"
        
        if sudo systemctl start docker; then
            echo -e "${GREEN}✓ Service Docker démarré${NC}"
            
            # Attendre que Docker soit prêt
            sleep 5
            
            if docker ps > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Docker est maintenant accessible !${NC}"
                exit 0
            fi
        fi
        
        echo -e "${RED}❌ Impossible de démarrer Docker${NC}"
        echo ""
        echo -e "${YELLOW}Actions suggérées:${NC}"
        echo "  1. Vérifier l'état: sudo systemctl status docker"
        echo "  2. Voir les logs: sudo journalctl -u docker"
        echo "  3. Ajouter votre user au groupe docker: sudo usermod -aG docker \$USER"
        exit 1
    else
        echo -e "${RED}❌ Docker n'est pas installé${NC}"
        echo ""
        echo -e "${YELLOW}Pour installer Docker:${NC}"
        echo "  curl -fsSL https://get.docker.com | sh"
        echo "  sudo systemctl enable docker"
        echo "  sudo systemctl start docker"
        exit 1
    fi
    
else
    echo -e "${RED}❌ Système d'exploitation non supporté: $OSTYPE${NC}"
    exit 1
fi

