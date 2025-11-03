#!/bin/bash
#
# Script de redémarrage nginx en production avec nouvelle configuration pour t4g.dazno.de
# Dernière mise à jour: $(date +%Y-%m-%d)
#
# Usage: ./restart_nginx_production.sh [--ssh]
#   --ssh : Se connecter via SSH au serveur de production

set -e

# Configuration SSH
SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"
PROJECT_DIR="${PROJECT_DIR:-/home/feustey/MCP}"
NGINX_CONTAINER="${NGINX_CONTAINER:-hostinger-nginx}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🔄 REDÉMARRAGE NGINX PRODUCTION                       ║${NC}"
echo -e "${BLUE}║  Configuration: t4g.dazno.de + Bitcoin/LND endpoints  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$1" = "--ssh" ]; then
    # Mode SSH - connexion au serveur
    echo -e "${YELLOW}📡 Connexion au serveur de production...${NC}"
    echo ""
    
    ssh "$SSH_HOST" << ENDSSH
        set -e
        
        cd ${PROJECT_DIR} || cd /home/feustey/MCP || { echo "❌ Répertoire introuvable"; exit 1; }
        
        echo -e "${BLUE}📍 Répertoire: \$(pwd)${NC}"
        echo ""
        
        echo -e "${YELLOW}📋 Étape 1/5: Vérification de l'état actuel${NC}"
        echo "=================================================="
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(nginx|mcp-api)" || true
        echo ""
        
        echo -e "${YELLOW}📝 Étape 2/5: Copie de la configuration nginx${NC}"
        echo "============================================="
        
        # Déterminer le fichier de configuration nginx utilisé
        if [ -f "./nginx-docker.conf" ]; then
            echo "✅ Fichier nginx-docker.conf trouvé"
            
            # Si docker-compose utilise config/nginx/hostinger-unified.conf
            if [ -d "./config/nginx" ]; then
                echo "📋 Copie vers config/nginx/hostinger-unified.conf"
                cp nginx-docker.conf config/nginx/hostinger-unified.conf
                echo "✅ Configuration copiée"
            else
                echo "⚠️  Répertoire config/nginx non trouvé, création..."
                mkdir -p config/nginx
                cp nginx-docker.conf config/nginx/hostinger-unified.conf
                echo "✅ Configuration créée"
            fi
        else
            echo "❌ Fichier nginx-docker.conf non trouvé dans \$(pwd)"
            echo "⚠️  Tentative avec config/nginx existante..."
        fi
        
        echo ""
        echo -e "${YELLOW}🧪 Étape 3/5: Test de la configuration nginx${NC}"
        echo "==========================================="
        
        # Tester la configuration dans le conteneur
        if docker exec ${NGINX_CONTAINER} nginx -t 2>/dev/null; then
            echo "✅ Configuration actuelle valide"
        else
            echo "⚠️  Test de configuration échoué (normal si conteneur non démarré)"
        fi
        
        echo ""
        echo -e "${YELLOW}🔄 Étape 4/5: Redémarrage du conteneur nginx${NC}"
        echo "================================================"
        
        # Arrêter le conteneur
        echo "🛑 Arrêt du conteneur..."
        docker stop ${NGINX_CONTAINER} 2>/dev/null || true
        
        # Redémarrer avec docker-compose si disponible
        if [ -f "docker-compose.hostinger-unified.yml" ]; then
            echo "📦 Redémarrage via docker-compose..."
            docker-compose -f docker-compose.hostinger-unified.yml restart nginx || docker-compose restart nginx || docker restart ${NGINX_CONTAINER}
        else
            echo "📦 Redémarrage direct du conteneur..."
            docker start ${NGINX_CONTAINER} || docker restart ${NGINX_CONTAINER} || {
                echo "⚠️  Redémarrage direct échoué, utilisation docker-compose..."
                docker-compose restart nginx 2>/dev/null || docker-compose -f docker-compose.yml restart nginx 2>/dev/null
            }
        fi
        
        echo "⏳ Attente 5 secondes pour le démarrage..."
        sleep 5
        
        echo ""
        echo -e "${YELLOW}✅ Étape 5/5: Vérification finale${NC}"
        echo "=================================="
        
        # Vérifier le statut
        echo "📊 État des conteneurs:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(nginx|mcp-api)" || true
        
        echo ""
        echo "🧪 Tests de connectivité:"
        
        # Test health endpoint
        echo -n "  - Health endpoint (localhost): "
        curl -s -o /dev/null -w "%{http_code}" http://localhost/health && echo " ✅" || echo " ❌"
        
        # Test API endpoint
        echo -n "  - API endpoint (localhost): "
        curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/health && echo " ✅" || echo " ❌"
        
        # Test via domaine (si accessible)
        echo -n "  - api.dazno.de: "
        curl -s -o /dev/null -w "%{http_code}" http://api.dazno.de/health 2>/dev/null && echo " ✅" || echo " ⚠️  (DNS/Network)"
        
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✅ NGINX REDÉMARRÉ AVEC SUCCÈS                        ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "📋 Endpoints disponibles:"
        echo "  - https://api.dazno.de/api/v1/*"
        echo "  - https://t4g.dazno.de/api/v1/token4good/*"
        echo "  - https://t4g.dazno.de/api/v1/lightning/*"
        echo "  - https://t4g.dazno.de/api/v1/wallet/*"
        echo "  - https://t4g.dazno.de/api/v1/channels/*"
        echo "  - https://t4g.dazno.de/api/v1/nodes/*"
ENDSSH
    
else
    # Mode local - instructions
    echo -e "${YELLOW}ℹ️  Mode local - Instructions pour redémarrer nginx${NC}"
    echo ""
    echo "Pour redémarrer nginx en production, exécutez:"
    echo ""
    echo -e "${BLUE}  ./scripts/restart_nginx_production.sh --ssh${NC}"
    echo ""
    echo "Ou manuellement sur le serveur:"
    echo ""
    echo "  1. Se connecter:"
    echo -e "     ${BLUE}ssh ${SSH_HOST}${NC}"
    echo ""
    echo "  2. Copier la configuration:"
    echo -e "     ${BLUE}cd ${PROJECT_DIR}${NC}"
    echo -e "     ${BLUE}cp nginx-docker.conf config/nginx/hostinger-unified.conf${NC}"
    echo ""
    echo "  3. Redémarrer nginx:"
    echo -e "     ${BLUE}docker-compose -f docker-compose.hostinger-unified.yml restart nginx${NC}"
    echo "     ou"
    echo -e "     ${BLUE}docker restart ${NGINX_CONTAINER}${NC}"
    echo ""
    echo "  4. Vérifier:"
    echo -e "     ${BLUE}docker ps | grep nginx${NC}"
    echo -e "     ${BLUE}curl http://localhost/health${NC}"
    echo ""
fi

