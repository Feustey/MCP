#!/bin/bash

# Couleurs pour la sortie
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# User agent de navigateur pour contourner le blocage
BROWSER_UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Fonction de test avec User-Agent de navigateur
test_endpoint() {
    local url=$1
    local expected_status=$2
    echo -e "\n🧪 Testing $url"
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "User-Agent: $BROWSER_UA" "$url")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✅ Success: Got expected status $response${NC}"
    else
        echo -e "${RED}❌ Error: Expected $expected_status but got $response${NC}"
    fi
}

# Test des endpoints principaux
echo "🔍 Testing MCP API endpoints..."

# Test HTTP (devrait rediriger vers HTTPS)
test_endpoint "http://api.dazno.de/health" "301"

# Test HTTPS health
test_endpoint "https://api.dazno.de/health" "200"

# Test API directe (contourne Nginx)
test_endpoint "http://147.79.101.32:8000/health" "200"

# Test métriques (devrait être bloqué sauf pour IPs locales)
test_endpoint "https://api.dazno.de/metrics" "403"

echo -e "\n✨ Tests terminés" 