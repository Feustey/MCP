#!/bin/bash
# Script pour corriger l'endpoint /health en production
# Corrige le trailing slash dans la configuration nginx

set -e

echo "🔧 Correction de l'endpoint /health en production"
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "nginx-docker.conf" ]; then
    echo "❌ Fichier nginx-docker.conf non trouvé"
    echo "   Assurez-vous d'être dans le répertoire racine MCP"
    exit 1
fi

# Vérifier que le conteneur nginx est en cours d'exécution
if ! docker ps | grep -q mcp-nginx; then
    echo "❌ Le conteneur mcp-nginx n'est pas en cours d'exécution"
    exit 1
fi

echo "✅ Conteneur nginx trouvé"
echo ""

# Copier la nouvelle configuration dans le conteneur
echo "📋 Copie de la nouvelle configuration nginx..."
docker cp nginx-docker.conf mcp-nginx:/etc/nginx/nginx.conf

if [ $? -eq 0 ]; then
    echo "✅ Configuration copiée avec succès"
else
    echo "❌ Échec de la copie de la configuration"
    exit 1
fi

echo ""
echo "🔍 Test de la configuration nginx..."
docker exec mcp-nginx nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Configuration nginx valide"
else
    echo "❌ Configuration nginx invalide - restauration nécessaire"
    exit 1
fi

echo ""
echo "🔄 Rechargement de nginx..."
docker exec mcp-nginx nginx -s reload

if [ $? -eq 0 ]; then
    echo "✅ Nginx rechargé avec succès"
else
    echo "❌ Échec du rechargement de nginx"
    exit 1
fi

echo ""
echo "⏳ Attente de 3 secondes pour la propagation..."
sleep 3

echo ""
echo "🧪 Test de l'endpoint /health..."
echo ""

# Test local (dans le réseau Docker)
echo "Test 1: Appel direct au conteneur mcp-api"
if docker exec mcp-api curl -s -f http://localhost:8000/health > /dev/null; then
    echo "  ✅ mcp-api répond sur /health"
else
    echo "  ⚠️  mcp-api ne répond pas sur /health (ou endpoint inexistant)"
fi

# Test via nginx (réseau Docker interne)
echo ""
echo "Test 2: Appel via nginx (réseau Docker)"
if docker exec mcp-nginx curl -s -f http://mcp-api:8000/health > /dev/null; then
    echo "  ✅ nginx peut atteindre mcp-api/health"
else
    echo "  ⚠️  nginx ne peut pas atteindre mcp-api/health"
fi

# Test externe (si accessible)
echo ""
echo "Test 3: Appel externe via curl"
EXTERNAL_URL="${EXTERNAL_URL:-http://api.dazno.de/health}"
echo "  URL testée: $EXTERNAL_URL"

RESPONSE=$(curl -s -w "\n%{http_code}" "$EXTERNAL_URL" 2>/dev/null || echo "ERROR")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Endpoint /health accessible (HTTP 200)"
    echo "  Réponse: $BODY"
elif [ "$HTTP_CODE" = "ERROR" ]; then
    echo "  ⚠️  Impossible de joindre l'URL (erreur réseau?)"
else
    echo "  ❌ Endpoint répond avec le code HTTP: $HTTP_CODE"
    echo "  Réponse: $BODY"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Correction appliquée !"
echo ""
echo "📌 Résumé du changement:"
echo "   Avant: proxy_pass http://mcp-api/;  (redirige /health vers /)"
echo "   Après:  proxy_pass http://mcp-api;   (préserve le path /health)"
echo ""
echo "📝 Si le test externe a échoué, vérifiez:"
echo "   1. Que l'API FastAPI expose bien un endpoint /health"
echo "   2. Que le port 80 est bien mappé sur l'hôte"
echo "   3. Que le firewall autorise le trafic HTTP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

