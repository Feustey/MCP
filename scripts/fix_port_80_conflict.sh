#!/bin/bash
#
# Script pour résoudre le conflit de port 80 lors du démarrage de nginx
# Identifie ce qui utilise le port et propose des solutions
#
# Dernière mise à jour: 10 octobre 2025

set -e

echo "🔧 RÉSOLUTION CONFLIT PORT 80"
echo "=============================="
echo ""

SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"
PROJECT_DIR="${PROJECT_DIR:-/home/feustey/mcp-production}"

echo "📡 Connexion à ${SSH_HOST}..."
echo ""

ssh "$SSH_HOST" << 'ENDSSH'
    echo "🔍 Étape 1: Identifier ce qui utilise le port 80"
    echo "------------------------------------------------"
    
    echo "Processus utilisant le port 80:"
    sudo lsof -i :80 || echo "Impossible de lister (permissions requises)"
    
    echo ""
    sudo netstat -tulpn | grep :80 || echo "Aucun processus trouvé sur le port 80"
    
    echo ""
    echo "🐳 Étape 2: Vérifier les containers Docker sur port 80"
    echo "-------------------------------------------------------"
    docker ps -a --filter "publish=80" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "🛑 Étape 3: Arrêter le conflit"
    echo "------------------------------"
    
    # Vérifier si un ancien nginx tourne
    if docker ps | grep -E "nginx|mcp-nginx" | grep -v "mcp-nginx.*Created"; then
        echo "Arrêt de l'ancien container nginx..."
        docker ps | grep -E "nginx" | awk '{print $1}' | xargs -r docker stop || true
        docker ps -a | grep -E "nginx" | awk '{print $1}' | xargs -r docker rm -f || true
        echo "✅ Ancien nginx arrêté"
    fi
    
    # Vérifier si nginx système tourne
    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo "⚠️  Nginx système détecté (systemctl)"
        echo "Arrêt de nginx système..."
        sudo systemctl stop nginx || true
        sudo systemctl disable nginx || true
        echo "✅ Nginx système arrêté"
    fi
    
    # Vérifier si apache tourne
    if systemctl is-active --quiet apache2 2>/dev/null; then
        echo "⚠️  Apache détecté"
        echo "Arrêt d'Apache..."
        sudo systemctl stop apache2 || true
        echo "✅ Apache arrêté"
    fi
    
    echo ""
    echo "🔄 Étape 4: Redémarrage Docker Compose"
    echo "--------------------------------------"
    
    cd /home/feustey/mcp-production || cd /home/feustey/MCP || cd ~/mcp || {
        echo "❌ Répertoire introuvable"
        exit 1
    }
    
    # Redémarrer proprement
    docker-compose down || true
    sleep 3
    docker-compose up -d
    
    echo ""
    echo "⏳ Attente 20 secondes pour le démarrage..."
    sleep 20
    
    echo ""
    echo "✅ Étape 5: Vérification finale"
    echo "-------------------------------"
    docker-compose ps
    
    echo ""
    echo "🏥 Test de santé interne"
    if docker exec mcp-api wget -q -O- http://localhost:8000/health 2>/dev/null; then
        echo "✅ API répond correctement"
    else
        echo "⚠️  API ne répond pas encore (peut prendre plus de temps)"
        echo "Logs API:"
        docker-compose logs mcp-api --tail 20
    fi
ENDSSH

echo ""
echo "✅ Script terminé"
echo ""
echo "Prochaine vérification: curl https://api.dazno.de/health"


