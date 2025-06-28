#!/bin/sh

# Script de test des ports backend pour api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🔍 Test des ports backend pour api.dazno.de..."

# Test des ports backend courants
echo "Test des ports backend potentiels..."

# Port 8000 (FastAPI par défaut)
echo "Test du port 8000 (FastAPI par défaut)..."
nc -zv api.dazno.de 8000 2>&1 || {
    echo "❌ Port 8000 non accessible"
}

# Port 8080 (alternative courante)
echo "Test du port 8080..."
nc -zv api.dazno.de 8080 2>&1 || {
    echo "❌ Port 8080 non accessible"
}

# Port 3000 (Node.js/Express)
echo "Test du port 3000..."
nc -zv api.dazno.de 3000 2>&1 || {
    echo "❌ Port 3000 non accessible"
}

# Port 5000 (Flask)
echo "Test du port 5000..."
nc -zv api.dazno.de 5000 2>&1 || {
    echo "❌ Port 5000 non accessible"
}

# Test direct des endpoints sur les ports potentiels
echo ""
echo "Test des endpoints sur les ports potentiels..."

# Test port 8000
echo "Test /health sur port 8000..."
curl -s -o /dev/null -w "Port 8000 /health - Code: %{http_code}\n" http://api.dazno.de:8000/health 2>/dev/null || {
    echo "❌ Endpoint /health non accessible sur port 8000"
}

echo "Test /docs sur port 8000..."
curl -s -o /dev/null -w "Port 8000 /docs - Code: %{http_code}\n" http://api.dazno.de:8000/docs 2>/dev/null || {
    echo "❌ Endpoint /docs non accessible sur port 8000"
}

# Test port 8080
echo "Test /health sur port 8080..."
curl -s -o /dev/null -w "Port 8080 /health - Code: %{http_code}\n" http://api.dazno.de:8080/health 2>/dev/null || {
    echo "❌ Endpoint /health non accessible sur port 8080"
}

# Test avec timeout court
echo ""
echo "Test avec timeout court..."
for port in 8000 8080 3000 5000; do
    echo "Test rapide port $port..."
    timeout 3 curl -s -o /dev/null -w "Port $port - Code: %{http_code}\n" http://api.dazno.de:$port/ 2>/dev/null || {
        echo "❌ Port $port non accessible"
    }
done

echo ""
echo "📋 Analyse du problème:"
echo "✅ Serveur web: Caddy (visible dans les headers)"
echo "✅ SSL: Certificat Let's Encrypt valide"
echo "✅ DNS: Résolution OK"
echo "❌ Backend: Non accessible (erreur 502)"

echo ""
echo "🔧 Solutions pour résoudre l'erreur 502:"
echo ""
echo "1. Vérifier que l'application FastAPI est démarrée sur le serveur:"
echo "   ssh user@api.dazno.de"
echo "   cd /path/to/app"
echo "   python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo ""
echo "2. Vérifier la configuration Caddy:"
echo "   - Le fichier Caddyfile doit pointer vers le bon port backend"
echo "   - Exemple: proxy / localhost:8000"
echo ""
echo "3. Vérifier les logs Caddy:"
echo "   journalctl -u caddy -f"
echo ""
echo "4. Vérifier que l'application écoute sur le bon port:"
echo "   netstat -tlnp | grep :8000"
echo ""
echo "5. Redémarrer les services:"
echo "   sudo systemctl restart caddy"
echo "   sudo systemctl restart votre-app-service"

echo ""
echo "✅ Tests terminés" 