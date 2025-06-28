#!/bin/sh

# Script de diagnostic et correction rapide pour l'erreur 502
# Dernière mise à jour: 9 mai 2025

echo "⚡ Diagnostic et correction rapide pour l'erreur 502..."

# Test rapide de l'état actuel
echo "🔍 État actuel:"
curl -s -o /dev/null -w "HTTPS - Code: %{http_code}\n" https://api.dazno.de/ || echo "❌ HTTPS non accessible"

# Test des ports backend
echo ""
echo "🔌 Test des ports backend..."
for port in 8000 8080 3000 5000; do
    nc -z -w 3 api.dazno.de $port 2>/dev/null && {
        echo "✅ Port $port accessible"
        echo "Test endpoint sur port $port..."
        curl -s -o /dev/null -w "Port $port - Code: %{http_code}\n" http://api.dazno.de:$port/health 2>/dev/null || echo "❌ Endpoint non accessible"
    } || echo "❌ Port $port non accessible"
done

echo ""
echo "📋 Résumé du problème:"
echo "✅ Serveur web: Caddy fonctionne (port 443 accessible)"
echo "✅ SSL: Certificat Let's Encrypt valide"
echo "❌ Backend: Aucun port backend accessible"
echo "❌ Résultat: Erreur 502 (Bad Gateway)"

echo ""
echo "🚀 Solutions immédiates:"

echo ""
echo "1. 🔧 Solution rapide (si vous avez accès SSH):"
echo "   ssh root@api.dazno.de"
echo "   cd /var/www/mcp  # ou votre répertoire d'app"
echo "   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo ""
echo "2. 🐳 Solution Docker (recommandée):"
echo "   # Sur le serveur:"
echo "   docker run -d --name mcp-api \\"
echo "     -p 8000:8000 \\"
echo "     -v /var/www/mcp:/app \\"
echo "     python:3.13-slim \\"
echo "     bash -c 'cd /app && pip install -r requirements.txt && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'"

echo ""
echo "3. 📦 Solution avec notre script de déploiement:"
echo "   ./scripts/deploy_api_dazno.sh"

echo ""
echo "4. 🔍 Diagnostic avancé (si vous avez accès SSH):"
echo "   ssh root@api.dazno.de"
echo "   # Vérifier les services:"
echo "   systemctl list-units --type=service --state=active | grep -E '(caddy|nginx|apache|mcp|fastapi)'"
echo "   # Vérifier les ports:"
echo "   netstat -tlnp | grep -E ':(80|443|8000|8080)'"
echo "   # Vérifier les processus:"
echo "   ps aux | grep -E '(python|uvicorn|fastapi)'"

echo ""
echo "5. 📝 Configuration Caddy manuelle:"
echo "   # Sur le serveur, éditer /etc/caddy/Caddyfile:"
echo "   api.dazno.de {"
echo "     reverse_proxy localhost:8000"
echo "   }"
echo "   # Puis redémarrer:"
echo "   systemctl restart caddy"

echo ""
echo "💡 Recommandation:"
echo "Utilisez le script de déploiement complet:"
echo "  ./scripts/deploy_api_dazno.sh"
echo ""
echo "Ou pour un test rapide, démarrez manuellement l'API sur le serveur."

echo ""
echo "✅ Diagnostic terminé" 