#!/bin/bash

# Fix rapide pour rétablir l'accès aux APIs
set -e

echo "🚨 FIX RAPIDE API HOSTINGER"
echo "========================="

HOST="feustey@147.79.101.32"

# Test si l'API est déjà accessible directement
echo "🔍 Test de l'état actuel..."
if curl -s -m 5 http://147.79.101.32:8000/health >/dev/null 2>&1; then
    echo "✅ L'API est déjà accessible sur le port 8000"
    curl -s http://147.79.101.32:8000/health | head -3
else
    echo "❌ L'API n'est pas accessible, fix nécessaire"
    
    # Essayer de redémarrer juste l'API
    echo "🚀 Tentative de redémarrage de l'API..."
    
    # Script minimal à exécuter sur le serveur
    ssh -o ConnectTimeout=30 "$HOST" '
        echo "Arrêt conteneurs existants..."
        docker stop $(docker ps -q) 2>/dev/null || true
        
        echo "Démarrage API simple..."
        docker run -d --rm -p 8000:8000 \
            --name mcp-api-simple \
            -e HOST=0.0.0.0 \
            -e PORT=8000 \
            -e ENVIRONMENT=production \
            -e MONGO_URL=mongodb+srv://feustey:sIiEp8oiB2hjYBbi@dazia.pin4fwl.mongodb.net/mcp?retryWrites=true&w=majority&appName=Dazia \
            -e REDIS_URL=redis://default:EqbM5xJAkh9gvdOyVoYiWR9EoHRBXcjY@redis-16818.crce202.eu-west-3-1.ec2.redns.redis-cloud.com:16818/0 \
            --restart=unless-stopped \
            feustey/dazno:latest
        
        echo "Attente 30s..."
        sleep 30
        
        echo "État des conteneurs:"
        docker ps
    ' || echo "❌ SSH fix échoué"
fi

# Attendre un peu plus
echo "⏳ Attente supplémentaire..."
sleep 30

# Tests finaux
echo "🧪 TESTS FINAUX"
echo "=============="

echo "1. Test API direct (port 8000):"
if curl -s -m 10 http://147.79.101.32:8000/health 2>/dev/null; then
    echo "✅ API accessible sur port 8000"
    curl -s -m 5 http://147.79.101.32:8000/health | python3 -m json.tool 2>/dev/null || echo "Raw response OK"
else
    echo "❌ API non accessible sur port 8000"
fi

echo -e "\n2. Test domaine api.dazno.de:"
if curl -s -m 10 http://api.dazno.de/ 2>/dev/null | head -10; then
    echo "✅ Domaine api.dazno.de répond"
else
    echo "❌ Domaine api.dazno.de ne répond pas"
fi

echo -e "\n3. Test HTTPS:"
if curl -s -m 10 https://api.dazno.de/health 2>/dev/null | head -3; then
    echo "✅ HTTPS fonctionne"
else
    echo "❌ HTTPS ne fonctionne pas"
fi

echo -e "\n4. Test documentation:"
if curl -s -m 10 http://147.79.101.32:8000/docs 2>/dev/null | grep -i "swagger\|openapi" >/dev/null; then
    echo "✅ Documentation accessible"
    echo "📖 Docs: http://147.79.101.32:8000/docs"
else
    echo "❌ Documentation non accessible"
fi

echo -e "\n🎯 RÉSUMÉ:"
echo "========="
echo "• API Direct: http://147.79.101.32:8000"
echo "• API Health: http://147.79.101.32:8000/health"
echo "• API Docs: http://147.79.101.32:8000/docs"
echo "• Domaine: http://api.dazno.de"
echo "• HTTPS: https://api.dazno.de"

# Nettoyer
rm -f /tmp/server_fix.sh 2>/dev/null || true

echo -e "\n✅ Fix rapide terminé!"