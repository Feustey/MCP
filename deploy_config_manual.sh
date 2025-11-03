#!/bin/bash

# Script de déploiement manuel de config.py
# Le mot de passe SSH sera demandé interactivement

set -e

HOST="srv594809.hstgr.cloud"
USER="u115-pdvfcwqc2ubq"
LOCAL_CONFIG="/Users/stephanecourant/Documents/DAZ/MCP/MCP/config.py"
REMOTE_PATH="domains/api.dazno.de/MCP/"

echo ""
echo "=== Déploiement de config.py avec api.dazno.de autorisé ==="
echo ""

# Étape 1: Transfert du fichier
echo "[1/4] Transfert de config.py vers le serveur..."
scp "$LOCAL_CONFIG" "$USER@$HOST:$REMOTE_PATH" || {
    echo "❌ Erreur lors du transfert SCP"
    exit 1
}
echo "✅ Fichier transféré"

# Étape 2: Rebuild et restart via SSH
echo ""
echo "[2/4] Connexion SSH et rebuild du conteneur..."
ssh "$USER@$HOST" << 'ENDSSH'
cd domains/api.dazno.de/MCP

echo "[3/4] Vérification de la modification..."
grep -n "api.dazno.de.*app.dazno.de" config.py | head -1

echo ""
echo "[4/4] Reconstruction de l'image Docker..."
docker-compose -f docker-compose.hostinger.yml build mcp-api

echo ""
echo "Redémarrage du conteneur mcp-api..."
docker-compose -f docker-compose.hostinger.yml up -d mcp-api

sleep 8

echo ""
echo "=== Vérification du déploiement ==="
docker ps --filter name=mcp-api --format 'table {{.Names}}\t{{.Status}}'

echo ""
echo "Logs de démarrage (dernières lignes):"
docker logs mcp-api --tail=10 2>&1 | grep -E "(Configuration|started|Application)" || echo "En cours de démarrage..."

echo ""
echo "Test du endpoint /health..."
curl -s http://localhost:8000/health | head -1

ENDSSH

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✅ Déploiement terminé avec succès             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Modifications appliquées:"
echo "  ✅ config.py mis à jour avec 'api.dazno.de' dans allowed_hosts"
echo "  ✅ Image Docker reconstruite"
echo "  ✅ Conteneur mcp-api redémarré"
echo ""
echo "🌐 Testez maintenant:"
echo "   https://api.dazno.de/docs"
echo ""
echo "💡 Si l'erreur persiste, attendez 30-60 secondes."
echo ""
