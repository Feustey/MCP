#!/bin/bash
#
# Crée un docker-compose.override.yml pour corriger l'entrypoint
# Sans avoir à rebuild l'image
#
# Dernière mise à jour: 10 octobre 2025

set -e

echo "🔧 CRÉATION DOCKER COMPOSE OVERRIDE"
echo "====================================="
echo ""

SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"

echo "📡 Connexion à ${SSH_HOST}..."
echo ""

ssh "$SSH_HOST" << 'ENDSSH'
    cd /home/feustey/mcp-production || cd /home/feustey/MCP || cd ~/mcp
    
    echo "✍️  Création de docker-compose.override.yml..."
    
    cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  mcp-api:
    # Override l'entrypoint cassé
    entrypoint: []
    command: >
      sh -c "
        echo '🚀 Démarrage MCP API' && 
        echo 'Mode: production' && 
        echo 'Port: 8000' &&
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level info
      "
    # Ajouter les variables d'environnement manquantes
    environment:
      - ENVIRONMENT=production
      - PORT=8000
      - WORKERS=2
      - LOG_LEVEL=info
EOF
    
    echo "✅ docker-compose.override.yml créé"
    echo ""
    
    echo "📋 Contenu du override:"
    cat docker-compose.override.yml
    echo ""
    
    echo "🔄 Redémarrage avec le nouveau override..."
    docker-compose down mcp-api
    docker-compose up -d mcp-api
    
    echo ""
    echo "⏳ Attente 30 secondes pour le démarrage..."
    sleep 30
    
    echo ""
    echo "📊 État:"
    docker-compose ps
    
    echo ""
    echo "📄 Logs (30 dernières lignes):"
    docker-compose logs mcp-api --tail 30
    
    echo ""
    echo "🏥 Test healthcheck:"
    if docker exec mcp-api curl -sf http://localhost:8000/health; then
        echo ""
        echo "✅ API répond correctement !"
    else
        echo "⚠️  API ne répond pas encore"
        echo ""
        echo "Logs complets:"
        docker-compose logs mcp-api
    fi
ENDSSH

echo ""
echo "✅ Script terminé"


