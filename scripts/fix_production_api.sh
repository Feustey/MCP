#!/bin/bash
#
# Script de diagnostic et réparation de l'API MCP en production
# Corrige le problème 502 Bad Gateway
#
# Dernière mise à jour: 10 octobre 2025

set -e

echo "🔍 DIAGNOSTIC ET RÉPARATION MCP API"
echo "===================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
API_URL="${API_URL:-https://api.dazno.de}"
SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"

echo "📊 Étape 1: Test de l'API externe"
echo "--------------------------------"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" 2>/dev/null || echo "000")
echo "HTTP Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ API accessible et fonctionnelle${NC}"
    exit 0
elif [ "$HTTP_CODE" = "502" ]; then
    echo -e "${RED}❌ 502 Bad Gateway - Backend API down${NC}"
elif [ "$HTTP_CODE" = "000" ]; then
    echo -e "${RED}❌ Cannot reach API - Network error${NC}"
else
    echo -e "${YELLOW}⚠️  API returns $HTTP_CODE${NC}"
fi

echo ""
echo "🐳 Étape 2: Vérification Docker (SSH requis)"
echo "--------------------------------------------"

if [ -z "$SSH_HOST" ]; then
    echo -e "${YELLOW}⚠️  SSH_HOST non défini, skip étape Docker${NC}"
    exit 1
fi

echo "Connexion à $SSH_HOST..."

# Vérifier l'état des containers
ssh "$SSH_HOST" << 'ENDSSH'
    echo "📦 État des containers Docker:"
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep mcp || echo "Aucun container MCP trouvé"
    
    echo ""
    echo "🔍 Vérification du container mcp-api:"
    
    if docker ps | grep -q mcp-api; then
        echo "✅ Container mcp-api est UP"
        
        # Vérifier les logs récents
        echo ""
        echo "📄 Derniers logs (20 lignes):"
        docker logs mcp-api --tail 20 2>&1 | tail -20
        
        # Test healthcheck interne
        echo ""
        echo "🏥 Test healthcheck interne:"
        docker exec mcp-api wget -q -O- http://localhost:8000/health 2>/dev/null || echo "❌ Healthcheck interne failed"
        
    else
        echo "❌ Container mcp-api est DOWN"
        
        # Vérifier si l'image existe
        if docker images | grep -q mcp; then
            echo "✅ Image Docker existe"
            echo ""
            echo "🔄 Tentative de redémarrage..."
            docker-compose up -d mcp-api
            sleep 10
            
            if docker ps | grep -q mcp-api; then
                echo "✅ Container redémarré avec succès"
            else
                echo "❌ Échec du redémarrage"
                echo "Logs d'erreur:"
                docker-compose logs mcp-api --tail 50
            fi
        else
            echo "❌ Image Docker introuvable"
            echo "Exécuter: docker-compose build mcp-api"
        fi
    fi
    
    echo ""
    echo "🌐 Vérification Nginx:"
    docker ps | grep nginx && echo "✅ Nginx UP" || echo "❌ Nginx DOWN"
    
    echo ""
    echo "📊 Statistiques ressources:"
    docker stats --no-stream mcp-api 2>/dev/null || echo "Stats non disponibles"
ENDSSH

echo ""
echo "✅ Diagnostic terminé"
echo ""
echo "📋 Actions recommandées:"
echo "1. Si mcp-api est DOWN: docker-compose up -d mcp-api"
echo "2. Si mcp-api crashloop: Vérifier les variables d'environnement (.env)"
echo "3. Si Nginx 502 persiste: docker-compose restart nginx"
echo "4. Vérifier les logs: docker-compose logs -f mcp-api"

