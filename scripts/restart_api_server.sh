#!/bin/bash
# scripts/restart_api_server.sh - Redémarrage rapide du serveur API
# Dernière mise à jour: 7 janvier 2025

set -e

# Variables
API_SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

echo "🔄 === REDÉMARRAGE SERVEUR API ==="

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Test SSH
log "🔍 Test de connexion SSH..."
if sshpass -p "$SSH_PASS" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" "echo 'SSH OK'" 2>/dev/null; then
    log "✅ Connexion SSH établie"
else
    log "❌ Connexion SSH échouée"
    exit 1
fi

# Redémarrage des services
log "🔄 Redémarrage des services sur le serveur..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" << 'ENDSSH'
    # Redémarrage Docker
    sudo systemctl restart docker
    sleep 2
    
    # Redémarrage Nginx
    sudo systemctl restart nginx
    sleep 2
    
    # Vérification des services
    echo "Status Docker:"
    sudo systemctl status docker | grep "active" || echo "Docker status unknown"
    
    echo "Status Nginx:"
    sudo systemctl status nginx | grep "active" || echo "Nginx status unknown"
    
    # Vérification des conteneurs
    echo "Conteneurs Docker:"
    sudo docker ps || echo "No containers running"
ENDSSH

log "✅ Redémarrage terminé"

# Test final
log "🔍 Test des endpoints..."
sleep 5

if curl -s --connect-timeout 5 "https://api.dazno.de/health" > /dev/null 2>&1; then
    log "✅ API accessible"
else
    log "❌ API non accessible"
fi

echo "✅ Script terminé" 