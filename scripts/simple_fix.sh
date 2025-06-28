#!/bin/bash
# scripts/simple_fix.sh - Solution rapide et directe
# Dernière mise à jour: 7 janvier 2025

echo "🚀 === SOLUTION RAPIDE MCP ==="

# Variables
API_SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

# 1. Construction locale
echo "🔨 Construction de l'image..."
docker build -f Dockerfile.coolify -t mcp-api:latest . || exit 1

# 2. Test SSH
echo "🔍 Test SSH..."
if ! sshpass -p "$SSH_PASS" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" "echo OK" 2>/dev/null; then
    echo "❌ SSH failed"
    exit 1
fi

# 3. Arrêt des anciens conteneurs
echo "🛑 Arrêt des anciens conteneurs..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" \
    "sudo docker stop \$(sudo docker ps -q) 2>/dev/null || true"

# 4. Copie de l'image
echo "📤 Copie de l'image..."
docker save mcp-api:latest | gzip | \
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" \
    "gunzip | sudo docker load"

# 5. Démarrage du nouveau conteneur
echo "🚀 Démarrage du conteneur..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" \
    "sudo docker run -d --name mcp 