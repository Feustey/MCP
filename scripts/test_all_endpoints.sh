#!/bin/bash
# scripts/test_all_endpoints.sh - Test complet de tous les endpoints
# Dernière mise à jour: 7 janvier 2025

echo "🔍 === TEST COMPLET DE TOUS LES ENDPOINTS ==="
echo "==========================================="

# Variables
API_SERVER="147.79.101.32"
DOMAIN="api.dazno.de"
COOLIFY_URL="https://coolify.marshmaflow.app"

# Fonction de test avec timeout et détails
test_endpoint() {
    local url=$1
    local name=$2
    local timeout=${3:-10}
    
    echo -n "[$name] $url ... "
    
    # Test avec curl et récupération du code de statut
    response=$(curl -s -w "%{http_code}" --connect-timeout $timeout --max-time $timeout "$url" 2>/dev/null)
    http_code="${response: -3}"
    content="${response%???}"
    
    if [ "$http_code" -eq 200 ] 2>/dev/null; then
        echo "✅ OK (200)"
        if [ ${#content} -gt 0 ] && [ ${#content} -lt 200 ]; then
            echo "    └── Réponse: $content"
        fi
    elif [ "$http_code" -ge 300 ] && [ "$http_code" -lt 400 ] 2>/dev/null; then
        echo "🔄 REDIRECT ($http_code)"
    elif [ "$http_code" -ge 400 ] && [ "$http_code" -lt 500 ] 2>/dev/null; then
        echo "❌ CLIENT ERROR ($http_code)"
    elif [ "$http_code" -ge 500 ] 2>/dev/null; then
        echo "❌ SERVER ERROR ($http_code)"
    else
        echo "💀 NO RESPONSE"
    fi
}

# Test de connectivité réseau basique
echo "🌐 === TESTS DE CONNECTIVITÉ RÉSEAU ==="
echo ""

# Test ping (si disponible)
echo -n "[PING] $API_SERVER ... "
if ping -c 1 -W 2 $API_SERVER > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ KO (normal si firewall)"
fi

# Test SSH
echo -n "[SSH] $API_SERVER:22 ... "
if nc -z -w2 $API_SERVER 22 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

# Test ports HTTP/HTTPS
echo -n "[HTTP] $API_SERVER:80 ... "
if nc -z -w2 $API_SERVER 80 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

echo -n "[HTTPS] $API_SERVER:443 ... "
if nc -z -w2 $API_SERVER 443 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

echo -n "[API] $API_SERVER:8000 ... "
if nc -z -w2 $API_SERVER 8000 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

echo ""
echo "🔗 === TESTS DES ENDPOINTS HTTP ==="
echo ""

# Endpoints principaux
endpoints=(
    # Coolify
    "$COOLIFY_URL|Coolify Dashboard"
    
    # API directe sur serveur
    "http://$API_SERVER:8000|API Direct"
    "http://$API_SERVER:8000/health|Health Direct"
    "http://$API_SERVER:8000/docs|Docs Direct"
    "http://$API_SERVER:8000/openapi.json|OpenAPI Direct"
    
    # API via domaine HTTP
    "http://$DOMAIN|Domain HTTP"
    "http://$DOMAIN/health|Health HTTP"
    "http://$DOMAIN/docs|Docs HTTP"
    
    # API via domaine HTTPS
    "https://$DOMAIN|Domain HTTPS"
    "https://$DOMAIN/health|Health HTTPS"
    "https://$DOMAIN/docs|Docs HTTPS"
    "https://$DOMAIN/openapi.json|OpenAPI HTTPS"
    
    # Endpoints API spécifiques (v1)
    "https://$DOMAIN/api/v1/health|API v1 Health"
    "https://$DOMAIN/api/v1/metrics|API v1 Metrics"
    "https://$DOMAIN/api/v1/status|API v1 Status"
    
    # Endpoints de monitoring
    "https://$DOMAIN/metrics|Prometheus Metrics"
    "https://$DOMAIN/ready|Readiness"
    "https://$DOMAIN/live|Liveness"
)

# Test de tous les endpoints
for endpoint_info in "${endpoints[@]}"; do
    IFS='|' read -r url name <<< "$endpoint_info"
    test_endpoint "$url" "$name" 10
done

echo ""
echo "📊 === TESTS SPÉCIALISÉS ==="
echo ""

# Test avec User-Agent spécifique
echo -n "[USER-AGENT] https://$DOMAIN/health ... "
if curl -s -A "MCP-Monitor/1.0" --connect-timeout 5 "https://$DOMAIN/health" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

# Test avec headers spécifiques
echo -n "[HEADERS] https://$DOMAIN/health ... "
if curl -s -H "Accept: application/json" -H "Content-Type: application/json" --connect-timeout 5 "https://$DOMAIN/health" > /dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

# Test de la vitesse de réponse
echo -n "[SPEED] https://$DOMAIN/health ... "
response_time=$(curl -s -w "%{time_total}" -o /dev/null --connect-timeout 5 "https://$DOMAIN/health" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ OK (${response_time}s)"
else
    echo "❌ KO"
fi

echo ""
echo "🐳 === STATUT DOCKER (LOCAL) ==="
echo ""

# Docker local
echo "Conteneurs en cours d'exécution :"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "❌ Docker non accessible"

echo ""
echo "Images MCP disponibles :"
docker images | grep -E "(mcp|api)" 2>/dev/null || echo "❌ Aucune image MCP trouvée"

echo ""
echo "📋 === RÉSUMÉ FINAL ==="
echo ""

# Résumé des services critiques
critical_endpoints=(
    "https://$DOMAIN/health"
    "https://$DOMAIN/docs"
    "http://$API_SERVER:8000/health"
    "$COOLIFY_URL"
)

echo "🎯 SERVICES CRITIQUES :"
for endpoint in "${critical_endpoints[@]}"; do
    if curl -s --connect-timeout 3 "$endpoint" > /dev/null 2>&1; then
        echo "  ✅ $endpoint"
    else
        echo "  ❌ $endpoint"
    fi
done

echo ""
echo "📱 ACTIONS RECOMMANDÉES :"
echo ""

# Vérifier si au moins un endpoint fonctionne
working_endpoints=0
for endpoint in "${critical_endpoints[@]}"; do
    if curl -s --connect-timeout 3 "$endpoint" > /dev/null 2>&1; then
        ((working_endpoints++))
    fi
done

if [ $working_endpoints -eq 0 ]; then
    echo "🔴 CRITIQUE: Aucun endpoint ne répond"
    echo "  1. Vérifiez les logs Docker sur le serveur"
    echo "  2. Redémarrez les services via SSH"
    echo "  3. Vérifiez la configuration Nginx"
    echo "  4. Contactez l'hébergeur si nécessaire"
elif [ $working_endpoints -lt 3 ]; then
    echo "🟡 PARTIEL: Certains endpoints ne répondent pas"
    echo "  1. Vérifiez la configuration du proxy"
    echo "  2. Testez le certificat SSL"
    echo "  3. Vérifiez les logs d'application"
else
    echo "🟢 BON: La plupart des endpoints fonctionnent"
    echo "  1. Surveillez les performances"
    echo "  2. Activez le monitoring"
    echo "  3. Planifiez les mises à jour"
fi

echo ""
echo "✅ === TEST TERMINÉ ==="
echo ""
echo "🔗 Liens rapides :"
echo "  • API Health: https://$DOMAIN/health"
echo "  • API Docs: https://$DOMAIN/docs"
echo "  • Coolify: $COOLIFY_URL"
echo "  • Direct: http://$API_SERVER:8000/health" 