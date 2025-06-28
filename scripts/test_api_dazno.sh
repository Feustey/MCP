#!/bin/sh

# Script de test pour api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🌐 Test de connectivité pour api.dazno.de..."

# Test du port 80 (HTTP)
echo ""
echo "🔍 Test du port 80 (HTTP)..."
echo "Test de connexion TCP..."
nc -zv api.dazno.de 80 2>&1 || {
    echo "❌ Port 80 non accessible"
}

echo "Test HTTP..."
curl -s -o /dev/null -w "HTTP - Code: %{http_code}, Temps: %{time_total}s\n" http://api.dazno.de/ || {
    echo "❌ HTTP non accessible"
}

# Test du port 443 (HTTPS)
echo ""
echo "🔒 Test du port 443 (HTTPS)..."
echo "Test de connexion TCP..."
nc -zv api.dazno.de 443 2>&1 || {
    echo "❌ Port 443 non accessible"
}

echo "Test HTTPS..."
curl -s -o /dev/null -w "HTTPS - Code: %{http_code}, Temps: %{time_total}s\n" https://api.dazno.de/ || {
    echo "❌ HTTPS non accessible"
}

# Test de résolution DNS
echo ""
echo "📡 Test de résolution DNS..."
nslookup api.dazno.de || {
    echo "❌ Résolution DNS échouée"
}

# Test de ping
echo ""
echo "🏓 Test de ping..."
ping -c 3 api.dazno.de || {
    echo "❌ Ping échoué"
}

# Test des endpoints spécifiques
echo ""
echo "🎯 Test des endpoints spécifiques..."

# Test HTTP endpoints
echo "Test /health sur HTTP..."
curl -s -o /dev/null -w "HTTP /health - Code: %{http_code}\n" http://api.dazno.de/health || {
    echo "❌ Endpoint /health non accessible en HTTP"
}

echo "Test /docs sur HTTP..."
curl -s -o /dev/null -w "HTTP /docs - Code: %{http_code}\n" http://api.dazno.de/docs || {
    echo "❌ Endpoint /docs non accessible en HTTP"
}

# Test HTTPS endpoints
echo "Test /health sur HTTPS..."
curl -s -o /dev/null -w "HTTPS /health - Code: %{http_code}\n" https://api.dazno.de/health || {
    echo "❌ Endpoint /health non accessible en HTTPS"
}

echo "Test /docs sur HTTPS..."
curl -s -o /dev/null -w "HTTPS /docs - Code: %{http_code}\n" https://api.dazno.de/docs || {
    echo "❌ Endpoint /docs non accessible en HTTPS"
}

# Test de certificat SSL
echo ""
echo "🔐 Test du certificat SSL..."
openssl s_client -connect api.dazno.de:443 -servername api.dazno.de < /dev/null 2>/dev/null | openssl x509 -noout -dates || {
    echo "❌ Certificat SSL non accessible"
}

# Test de traceroute
echo ""
echo "🗺️ Test de traceroute..."
traceroute api.dazno.de 2>/dev/null || {
    echo "❌ Traceroute échoué"
}

echo ""
echo "✅ Tests terminés" 