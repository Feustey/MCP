#!/bin/bash

# Couleurs pour la sortie
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔍 Vérification de la configuration Nginx..."

# Test de la configuration
docker exec mcp-nginx nginx -t

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Configuration Nginx valide${NC}"
    echo "🔄 Rechargement de Nginx..."
    
    # Rechargement de la configuration
    docker exec mcp-nginx nginx -s reload
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Nginx rechargé avec succès${NC}"
        
        # Test immédiat des endpoints
        echo "🧪 Test des endpoints..."
        ./scripts/test_api_access.sh
    else
        echo -e "${RED}❌ Erreur lors du rechargement de Nginx${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Configuration Nginx invalide${NC}"
    exit 1
fi 