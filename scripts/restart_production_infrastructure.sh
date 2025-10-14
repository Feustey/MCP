#!/bin/bash
#
# Script de redémarrage complet de l'infrastructure MCP en production
# Résout le problème 502 Bad Gateway et containers DOWN
#
# Usage: ./restart_production_infrastructure.sh [--force-rebuild]
#
# Dernière mise à jour: 10 octobre 2025

set -e

echo "🔄 REDÉMARRAGE INFRASTRUCTURE MCP PRODUCTION"
echo "============================================="
echo ""

# Variables
SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"
PROJECT_DIR="${PROJECT_DIR:-/home/feustey/mcp-production}"
FORCE_REBUILD="$1"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📡 Connexion à ${SSH_HOST}...${NC}"
echo ""

ssh "$SSH_HOST" << ENDSSH
    set -e
    
    echo -e "${YELLOW}📍 Répertoire: ${PROJECT_DIR}${NC}"
    cd ${PROJECT_DIR} || cd /home/feustey/MCP || cd ~/mcp || { echo "❌ Répertoire introuvable"; exit 1; }
    
    echo ""
    echo "🛑 Étape 1: Arrêt des containers existants"
    echo "-------------------------------------------"
    docker-compose down || true
    
    echo ""
    echo "🧹 Étape 2: Nettoyage (optionnel)"
    echo "----------------------------------"
    if [ "$FORCE_REBUILD" = "--force-rebuild" ]; then
        echo "🔨 Mode force-rebuild activé"
        docker system prune -f || true
        docker volume prune -f || true
    else
        echo "ℹ️  Mode normal (utiliser --force-rebuild pour nettoyage complet)"
    fi
    
    echo ""
    echo "📦 Étape 3: Pull des images"
    echo "----------------------------"
    docker-compose pull || echo "⚠️  Certaines images n'ont pas pu être téléchargées"
    
    echo ""
    echo "🚀 Étape 4: Démarrage des services"
    echo "-----------------------------------"
    docker-compose up -d
    
    echo ""
    echo "⏳ Étape 5: Attente démarrage (30 secondes)..."
    echo "-----------------------------------------------"
    sleep 30
    
    echo ""
    echo "🔍 Étape 6: Vérification de l'état"
    echo "-----------------------------------"
    docker-compose ps
    
    echo ""
    echo "🏥 Étape 7: Test de santé"
    echo "--------------------------"
    
    # Test healthcheck interne
    echo "Test interne API:"
    if docker exec mcp-api wget -q -O- http://localhost:8000/health 2>/dev/null; then
        echo -e "${GREEN}✅ API répond correctement en interne${NC}"
    else
        echo -e "${RED}❌ API ne répond pas en interne${NC}"
        echo "Logs API:"
        docker-compose logs mcp-api --tail 30
    fi
    
    echo ""
    echo "Test via nginx:"
    if docker exec mcp-nginx wget -q -O- http://mcp-api:8000/health 2>/dev/null; then
        echo -e "${GREEN}✅ Nginx peut atteindre l'API${NC}"
    else
        echo -e "${RED}❌ Nginx ne peut pas atteindre l'API${NC}"
    fi
    
    echo ""
    echo "📊 Étape 8: Statistiques ressources"
    echo "------------------------------------"
    docker stats --no-stream | head -5
    
    echo ""
    echo -e "${GREEN}✅ REDÉMARRAGE TERMINÉ${NC}"
    echo ""
    echo "📋 Vérifications recommandées:"
    echo "1. Test externe: curl https://api.dazno.de/health"
    echo "2. Surveiller logs: docker-compose logs -f mcp-api"
    echo "3. Vérifier monitoring: tail -f logs/monitoring.log"
ENDSSH

echo ""
echo -e "${BLUE}🌐 Test externe de l'API...${NC}"
echo ""

sleep 5

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.dazno.de/health 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ API ACCESSIBLE ET FONCTIONNELLE !${NC}"
    echo ""
    echo "📊 Réponse complète:"
    curl -s https://api.dazno.de/health | jq . 2>/dev/null || curl -s https://api.dazno.de/health
elif [ "$HTTP_CODE" = "502" ]; then
    echo -e "${RED}❌ Still 502 Bad Gateway${NC}"
    echo "Attendre 30s supplémentaires et réessayer..."
elif [ "$HTTP_CODE" = "000" ]; then
    echo -e "${RED}❌ Cannot reach API${NC}"
else
    echo -e "${YELLOW}⚠️  API returns HTTP $HTTP_CODE${NC}"
fi

echo ""
echo "🎉 Script terminé !"
echo ""
echo "Prochaines étapes:"
echo "1. Vérifier que le monitoring détecte l'API: python3 monitor_production.py"
echo "2. Consulter le rapport d'investigation: docs/investigation_failures_monitoring_20251010.md"

