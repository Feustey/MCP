#!/bin/bash

# Test complet de l'API v1 après déploiement des modules
# Vérifie tous les nouveaux endpoints

set -euo pipefail

API_URL="https://api.dazno.de"
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔍 TEST COMPLET API v1 - TOUS LES MODULES${NC}"
echo "============================================================"
echo "Timestamp: $(date)"
echo "============================================================\n"

# Compteurs
TOTAL=0
AVAILABLE=0
AUTH_REQUIRED=0
NOT_DEPLOYED=0

test_endpoint() {
    local endpoint="$1"
    local name="$2"
    local method="${3:-GET}"
    
    ((TOTAL++))
    
    local response_code
    if [[ "$method" == "POST" ]]; then
        response_code=$(curl -s -X POST -H "Content-Type: application/json" \
            -d '{"test": true}' -w "%{http_code}" -o /dev/null "$API_URL$endpoint" --max-time 5 || echo "000")
    else
        response_code=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL$endpoint" --max-time 5 || echo "000")
    fi
    
    case $response_code in
        200|201|204)
            ((AVAILABLE++))
            echo -e "  ${GREEN}✅ $endpoint${NC} ($response_code) - $name"
            ;;
        401|403)
            ((AUTH_REQUIRED++))
            echo -e "  ${YELLOW}🔒 $endpoint${NC} ($response_code) - $name (Auth requise)"
            ;;
        404)
            ((NOT_DEPLOYED++))
            echo -e "  ${RED}⏳ $endpoint${NC} ($response_code) - $name (Non déployé)"
            ;;
        *)
            echo -e "  ${RED}❌ $endpoint${NC} ($response_code) - $name (Erreur)"
            ;;
    esac
}

echo -e "${CYAN}📍 ENDPOINTS DE BASE${NC}"
test_endpoint "/" "API Root"
test_endpoint "/health" "Health Check"
test_endpoint "/health/live" "Liveness Probe"
test_endpoint "/info" "System Info"
test_endpoint "/docs" "Documentation"

echo -e "\n${CYAN}📊 ENDPOINTS MÉTRIQUES${NC}"
test_endpoint "/metrics" "Métriques principales"
test_endpoint "/metrics/detailed" "Métriques détaillées"
test_endpoint "/metrics/prometheus" "Export Prometheus"
test_endpoint "/metrics/dashboard" "Dashboard"
test_endpoint "/metrics/performance" "Performance"
test_endpoint "/metrics/redis" "Métriques Redis"

echo -e "\n${CYAN}🎯 API v1 - ENDPOINTS PRINCIPAUX${NC}"
test_endpoint "/api/v1/" "API v1 Root"
test_endpoint "/api/v1/health" "API v1 Health"
test_endpoint "/api/v1/status" "System Status"

echo -e "\n${CYAN}🔍 MODULE RAG${NC}"
test_endpoint "/api/v1/rag/health" "RAG Health"
test_endpoint "/api/v1/rag/query" "RAG Query" "POST"
test_endpoint "/api/v1/rag/ingest" "RAG Ingest" "POST"
test_endpoint "/api/v1/rag/analyze" "RAG Analyze" "POST"
test_endpoint "/api/v1/rag/validate" "RAG Validate" "POST"
test_endpoint "/api/v1/rag/benchmark" "RAG Benchmark" "POST"

echo -e "\n${CYAN}🧠 MODULE INTELLIGENCE${NC}"
test_endpoint "/api/v1/intelligence/analyze" "Intelligence Analyze" "POST"
test_endpoint "/api/v1/intelligence/predict" "Intelligence Predict" "POST"
test_endpoint "/api/v1/intelligence/recommend" "Intelligence Recommend" "POST"
test_endpoint "/api/v1/intelligence/insights" "Intelligence Insights"
test_endpoint "/api/v1/intelligence/network-analysis" "Network Analysis"

echo -e "\n${CYAN}⚡ MODULE OPTIMISATION${NC}"
test_endpoint "/api/v1/optimize/node/test123" "Node Optimization" "POST"
test_endpoint "/api/v1/optimize/channels" "Channel Optimization" "POST"
test_endpoint "/api/v1/optimize/fees" "Fee Optimization" "POST"
test_endpoint "/api/v1/optimize/routing" "Routing Optimization" "POST"
test_endpoint "/api/v1/optimize/liquidity" "Liquidity Optimization" "POST"

echo -e "\n${CYAN}🎮 MODULE SIMULATION${NC}"
test_endpoint "/api/v1/simulate/node" "Node Simulation" "POST"
test_endpoint "/api/v1/simulate/profiles" "Simulation Profiles"

echo -e "\n${CYAN}🔐 ENDPOINTS PROTÉGÉS${NC}"
test_endpoint "/api/v1/admin/metrics" "Admin Metrics"
test_endpoint "/api/v1/admin/maintenance" "Admin Maintenance" "POST"
test_endpoint "/api/v1/storage/upload" "File Upload" "POST"
test_endpoint "/api/v1/storage/download" "File Download"

# Résumé
echo -e "\n${BLUE}📊 RÉSUMÉ DES TESTS${NC}"
echo "============================================================"

deployment_rate=$((AVAILABLE * 100 / TOTAL))
total_functional=$((AVAILABLE + AUTH_REQUIRED))
functional_rate=$((total_functional * 100 / TOTAL))

echo "Total des endpoints testés: $TOTAL"
echo "Endpoints disponibles: $AVAILABLE"
echo "Endpoints protégés (auth requise): $AUTH_REQUIRED"
echo "Endpoints non déployés: $NOT_DEPLOYED"
echo ""

if [[ $functional_rate -ge 80 ]]; then
    echo -e "Statut: ${GREEN}✅ API v1 OPÉRATIONNELLE${NC}"
    status_emoji="✅"
    status_text="OPÉRATIONNELLE"
elif [[ $functional_rate -ge 50 ]]; then
    echo -e "Statut: ${YELLOW}⚠️  API v1 PARTIELLEMENT OPÉRATIONNELLE${NC}"
    status_emoji="⚠️"
    status_text="PARTIELLEMENT OPÉRATIONNELLE"
else
    echo -e "Statut: ${RED}❌ API v1 NON OPÉRATIONNELLE${NC}"
    status_emoji="❌"
    status_text="NON OPÉRATIONNELLE"
fi

echo "Taux de déploiement: $deployment_rate%"
echo "Taux fonctionnel: $functional_rate%"

# Notification Telegram
message="$status_emoji <b>API v1 - TEST COMPLET</b>

📅 $(date '+%d/%m/%Y à %H:%M')

📊 <b>Résultats:</b>
┣━ Total endpoints: $TOTAL
┣━ Disponibles: $AVAILABLE
┣━ Protégés: $AUTH_REQUIRED
┣━ Non déployés: $NOT_DEPLOYED
┗━ Taux fonctionnel: $functional_rate%

🎯 <b>Statut: $status_text</b>

🚀 Modules testés:
• 📍 Base: 5 endpoints
• 📊 Métriques: 6 endpoints  
• 🔍 RAG: 6 endpoints
• 🧠 Intelligence: 5 endpoints
• ⚡ Optimisation: 5 endpoints
• 🎮 Simulation: 2 endpoints
• 🔐 Admin: 4 endpoints

🤖 Test automatique terminé"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="$message" \
    -d parse_mode="HTML" > /dev/null 2>&1 || true

echo -e "\n${GREEN}✅ Test terminé! Notification envoyée.${NC}"

# Recommandations finales
echo -e "\n${BLUE}💡 RECOMMANDATIONS${NC}"
if [[ $NOT_DEPLOYED -gt 0 ]]; then
    echo "• $NOT_DEPLOYED endpoint(s) nécessitent un redéploiement complet"
    echo "• Vérifier que tous les modules sont bien chargés"
    echo "• Redémarrer les services si nécessaire"
fi

if [[ $AUTH_REQUIRED -gt 0 ]]; then
    echo "• $AUTH_REQUIRED endpoint(s) protégés - authentification configurée"
    echo "• Tester avec des tokens JWT valides"
fi

if [[ $AVAILABLE -gt 0 ]]; then
    echo "• $AVAILABLE endpoint(s) opérationnels - prêts pour l'intégration"
    echo "• API v1 fonctionnelle pour les applications clients"
fi