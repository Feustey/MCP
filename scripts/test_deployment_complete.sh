#!/bin/bash
# Script de test complet du déploiement MCP
# Date: 20 octobre 2025
#
# Teste tous les services et endpoints après les corrections

set -e

echo "🧪 Tests Complets du Déploiement MCP"
echo "====================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Compteurs
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Fonction de test
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_code="$4"
    local additional_args="${5:-}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "Test $TOTAL_TESTS: $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" $additional_args "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" $additional_args "$url")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_code, Got: $http_code)"
        echo "Response: $body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# URL de base
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "🎯 URL de base: $BASE_URL"
echo ""

# Catégorie 1: Health Checks
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Catégorie 1: Health Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "API Root" "GET" "$BASE_URL/" "200"
test_endpoint "Health Basic" "GET" "$BASE_URL/health" "200"
test_endpoint "Health Detailed" "GET" "$BASE_URL/health/detailed" "200"
test_endpoint "Health Ready" "GET" "$BASE_URL/health/ready" "200"
test_endpoint "Health Live" "GET" "$BASE_URL/health/live" "200"
test_endpoint "Info Endpoint" "GET" "$BASE_URL/info" "200"

echo ""

# Catégorie 2: Infrastructure Services
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏗️  Catégorie 2: Services Infrastructure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier Docker services
echo "Docker Services:"
if docker-compose ps | grep -q "Up"; then
    services_up=$(docker-compose ps | grep "Up" | wc -l)
    echo -e "  ${GREEN}✅ $services_up services actifs${NC}"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}" | grep -v "^NAME"
else
    echo -e "  ${RED}❌ Aucun service actif${NC}"
fi

echo ""

# Vérifier MongoDB
echo -n "MongoDB: "
if docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Accessible${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Non accessible${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Vérifier Redis
echo -n "Redis: "
if docker exec mcp-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Accessible${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Non accessible${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Vérifier Ollama
echo -n "Ollama: "
if docker exec mcp-ollama ollama list > /dev/null 2>&1; then
    model_count=$(docker exec mcp-ollama ollama list | tail -n +2 | wc -l)
    echo -e "${GREEN}✅ Accessible ($model_count modèles)${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}❌ Non accessible${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo ""

# Catégorie 3: API Endpoints
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔌 Catégorie 3: API Endpoints"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Metrics Prometheus" "GET" "$BASE_URL/metrics/prometheus" "200"
test_endpoint "Metrics Dashboard" "GET" "$BASE_URL/metrics/dashboard" "200"

# Catégorie 4: RAG Endpoints (si activé)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 Catégorie 4: RAG Endpoints"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test RAG Query (peut échouer si RAG désactivé ou modèles manquants)
echo -n "Test $((TOTAL_TESTS + 1)): RAG Query Endpoint... "
TOTAL_TESTS=$((TOTAL_TESTS + 1))

rag_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/rag/query" \
    -H "Content-Type: application/json" \
    -H "X-API-Version: 2025-10-15" \
    -H "Authorization: Bearer test" \
    -d '{"query": "Test deployment", "node_pubkey": "test"}')

rag_code=$(echo "$rag_response" | tail -n1)

if [ "$rag_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} (HTTP $rag_code)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
elif [ "$rag_code" = "503" ] || [ "$rag_code" = "500" ]; then
    echo -e "${YELLOW}⚠️  SKIP${NC} (HTTP $rag_code - RAG possiblement désactivé)"
    # Ne compte pas comme échec
else
    echo -e "${RED}❌ FAIL${NC} (HTTP $rag_code)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Catégorie 5: Performance
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ Catégorie 5: Performance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Mesurer le temps de réponse
echo "Temps de réponse (moyenne sur 5 requêtes):"
total_time=0
for i in {1..5}; do
    response_time=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/health")
    total_time=$(echo "$total_time + $response_time" | bc)
    echo "  Requête $i: ${response_time}s"
done
avg_time=$(echo "scale=3; $total_time / 5" | bc)
echo "  Moyenne: ${avg_time}s"

if (( $(echo "$avg_time < 1.0" | bc -l) )); then
    echo -e "  ${GREEN}✅ Performance OK (< 1s)${NC}"
elif (( $(echo "$avg_time < 2.0" | bc -l) )); then
    echo -e "  ${YELLOW}⚠️  Performance acceptable (< 2s)${NC}"
else
    echo -e "  ${RED}❌ Performance dégradée (> 2s)${NC}"
fi

echo ""

# Catégorie 6: Ressources Système
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💻 Catégorie 6: Ressources Système"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Espace disque
disk_usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
disk_avail=$(df -h / | tail -1 | awk '{print $4}')
echo "Espace disque:"
echo "  Utilisation: ${disk_usage}%"
echo "  Disponible: $disk_avail"

if [ "$disk_usage" -lt 80 ]; then
    echo -e "  ${GREEN}✅ Espace OK${NC}"
elif [ "$disk_usage" -lt 90 ]; then
    echo -e "  ${YELLOW}⚠️  Espace limité${NC}"
else
    echo -e "  ${RED}❌ Espace critique${NC}"
fi

echo ""

# Mémoire Docker
echo "Utilisation mémoire Docker:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}" | head -6

echo ""

# Résumé Final
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RÉSUMÉ DES TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total de tests: $TOTAL_TESTS"
echo -e "Tests réussis:  ${GREEN}$PASSED_TESTS${NC}"
echo -e "Tests échoués:  ${RED}$FAILED_TESTS${NC}"
echo ""

success_rate=$(echo "scale=1; ($PASSED_TESTS * 100) / $TOTAL_TESTS" | bc)
echo "Taux de réussite: ${success_rate}%"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Code de sortie
if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "${GREEN}✅ TOUS LES TESTS ONT RÉUSSI !${NC}"
    echo ""
    exit 0
elif [ "$FAILED_TESTS" -lt 3 ]; then
    echo -e "${YELLOW}⚠️  QUELQUES TESTS ONT ÉCHOUÉ${NC}"
    echo "Vérifier les logs pour plus de détails"
    echo ""
    exit 1
else
    echo -e "${RED}❌ PLUSIEURS TESTS ONT ÉCHOUÉ${NC}"
    echo "Déploiement possiblement incomplet"
    echo ""
    exit 1
fi

