#!/bin/sh

# Script de diagnostic et résolution pour l'erreur 502 sur api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🔧 Diagnostic et résolution de l'erreur 502 sur api.dazno.de..."

# Analyse des résultats du test
echo "📊 Analyse des résultats..."
echo "✅ Port 80: Accessible (redirection 308)"
echo "❌ Port 443: Erreur 502 (Bad Gateway)"
echo "✅ DNS: Résolution OK (147.79.101.32)"
echo "❌ Ping: Échec (timeout)"

echo ""
echo "🔍 Diagnostic de l'erreur 502..."

# Test détaillé HTTPS avec plus d'informations
echo "Test HTTPS détaillé..."
curl -v https://api.dazno.de/ 2>&1 | head -20

# Test des headers
echo ""
echo "Test des headers HTTPS..."
curl -I https://api.dazno.de/ 2>&1

# Test avec différents User-Agents
echo ""
echo "Test avec User-Agent..."
curl -H "User-Agent: Mozilla/5.0" -s -o /dev/null -w "HTTPS avec UA - Code: %{http_code}\n" https://api.dazno.de/

# Test de la configuration SSL
echo ""
echo "Test de la configuration SSL..."
openssl s_client -connect api.dazno.de:443 -servername api.dazno.de < /dev/null 2>/dev/null | grep -E "(subject|issuer|notAfter)" || {
    echo "❌ Problème avec le certificat SSL"
}

# Vérification des ports ouverts
echo ""
echo "Scan des ports ouverts..."
nmap -p 80,443,8000,8080 api.dazno.de 2>/dev/null || {
    echo "Test avec telnet..."
    telnet api.dazno.de 443 2>&1 | head -5
}

# Test de proxy/reverse proxy
echo ""
echo "Test de proxy..."
curl -H "X-Forwarded-For: 127.0.0.1" -s -o /dev/null -w "Avec X-Forwarded-For - Code: %{http_code}\n" https://api.dazno.de/

# Test de timeout
echo ""
echo "Test de timeout..."
curl --connect-timeout 10 --max-time 30 -s -o /dev/null -w "Timeout test - Code: %{http_code}\n" https://api.dazno.de/

echo ""
echo "💡 Solutions possibles pour l'erreur 502:"
echo "1. Le serveur backend (FastAPI) n'est pas démarré"
echo "2. Le reverse proxy (Nginx) ne peut pas se connecter au backend"
echo "3. Le backend écoute sur un port différent (8000 au lieu de 443)"
echo "4. Problème de configuration du reverse proxy"
echo "5. Le backend crash ou ne répond pas"

echo ""
echo "🚀 Actions recommandées:"
echo "1. Vérifier que l'application FastAPI est démarrée sur le serveur"
echo "2. Vérifier la configuration Nginx/Apache"
echo "3. Vérifier les logs du serveur web"
echo "4. Redémarrer l'application backend"
echo "5. Vérifier que l'application écoute sur le bon port"

echo ""
echo "✅ Diagnostic terminé" 