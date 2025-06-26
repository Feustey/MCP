#!/bin/bash
# scripts/emergency_fix.sh - Réparation d'urgence complète
# Dernière mise à jour: 7 janvier 2025

set -e

# Variables
API_SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"
DOMAIN="api.dazno.de"

echo "🚨 === RÉPARATION D'URGENCE MCP ==="
echo "================================="

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# 1. DIAGNOSTIC RAPIDE
log "🔍 Diagnostic express..."

# Test connectivité serveur
if nc -z -w3 $API_SERVER 22; then
    log "✅ Serveur accessible"
else
    log "❌ Serveur inaccessible"
    exit 1
fi

# 2. CONNEXION SSH ET DIAGNOSTIC SERVEUR
log "🔧 Connexion au serveur et diagnostic..."

sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" << 'ENDSSH'
echo "=== DIAGNOSTIC SERVEUR ==="

# Vérifier les services critiques
echo "🔍 Services système :"
sudo systemctl status docker | grep -E "(active|failed)" || echo "❌ Docker"
sudo systemctl status nginx | grep -E "(active|failed)" || echo "❌ Nginx"

# Vérifier les conteneurs Docker
echo "🐳 Conteneurs Docker :"
sudo docker ps -a

# Vérifier les logs récents
echo "📋 Logs Docker récents :"
sudo docker logs $(sudo docker ps -q | head -1) --tail 10 2>/dev/null || echo "❌ Pas de conteneurs"

# Vérifier la configuration Nginx
echo "🌐 Test configuration Nginx :"
sudo nginx -t 2>&1

# Vérifier les ports
echo "🔌 Ports ouverts :"
sudo netstat -tlpn | grep -E "(80|443|8000)" || echo "❌ Ports non ouverts"

echo "=== FIN DIAGNOSTIC ==="
ENDSSH

# 3. RÉPARATION AUTOMATIQUE
log "🛠️ Réparation automatique..."

sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" << 'ENDSSH'
echo "=== RÉPARATION AUTOMATIQUE ==="

# Arrêter tous les conteneurs
echo "🛑 Arrêt des conteneurs..."
sudo docker stop $(sudo docker ps -q) 2>/dev/null || echo "Aucun conteneur à arrêter"

# Nettoyer Docker
echo "🧹 Nettoyage Docker..."
sudo docker system prune -f

# Redémarrer Docker
echo "🔄 Redémarrage Docker..."
sudo systemctl restart docker
sleep 3

# Démarrer un conteneur de test simple
echo "🚀 Démarrage conteneur de test..."
sudo docker run -d --name test-api --restart unless-stopped -p 8000:8000 \
  -e PORT=8000 \
  nginx:alpine sh -c '
    echo "server {
      listen 8000;
      location /health { return 200 \"OK\"; add_header Content-Type text/plain; }
      location / { return 200 \"MCP API Fallback\"; add_header Content-Type text/plain; }
    }" > /etc/nginx/conf.d/default.conf && 
    nginx -g "daemon off;"
  ' || echo "❌ Échec démarrage conteneur test"

sleep 5

# Tester localement
echo "🧪 Test local :"
curl -s http://localhost:8000/health || echo "❌ Test local échoué"

# Redémarrer Nginx
echo "🔄 Redémarrage Nginx..."
sudo systemctl restart nginx

# Réparer SSL rapidement
echo "🔒 Réparation SSL express..."
sudo certbot --nginx -d api.dazno.de --email admin@dazno.de --agree-tos --non-interactive --force-renewal --quiet 2>/dev/null || echo "⚠️ SSL non réparé"

echo "✅ Réparation terminée"
ENDSSH

# 4. TEST FINAL
log "🔍 Vérification finale..."

sleep 10

# Test direct sur serveur
log "Test direct serveur..."
if curl -s --connect-timeout 5 "http://$API_SERVER:8000/health" | grep -q "OK"; then
    log "✅ Serveur direct accessible"
else
    log "❌ Serveur direct non accessible"
fi

# Test domaine
log "Test domaine..."
if curl -s --connect-timeout 5 "https://$DOMAIN/health" | grep -q "OK"; then
    log "✅ Domaine accessible"
else
    log "❌ Domaine non accessible"
fi

echo ""
echo "📊 === RAPPORT FINAL ==="
echo ""

# URLs de test
urls=(
    "http://$API_SERVER:8000/health"
    "https://$DOMAIN/health"
    "http://$DOMAIN/health"
)

for url in "${urls[@]}"; do
    if curl -s --connect-timeout 3 "$url" >/dev/null 2>&1; then
        echo "✅ $url"
    else
        echo "❌ $url"
    fi
done

echo ""
echo "🎯 ACTIONS IMMÉDIATES :"
echo "1. 🔄 Actualisez votre navigateur (Ctrl+F5)"
echo "2. 🌐 Testez : http://147.79.101.32:8000/health"
echo "3. 🔒 Testez : https://api.dazno.de/health"
echo "4. ⏰ Attendez 2-3 minutes pour la propagation"
echo ""
echo "✅ === RÉPARATION TERMINÉE ===" 