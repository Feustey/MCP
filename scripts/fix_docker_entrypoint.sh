#!/bin/bash
#
# Script pour corriger l'entrypoint Docker et redémarrer l'API
# Crée un start.sh correct directement sur le serveur
#
# Dernière mise à jour: 10 octobre 2025

set -e

echo "🔧 CORRECTION ENTRYPOINT DOCKER MCP"
echo "===================================="
echo ""

SSH_HOST="${SSH_HOST:-feustey@147.79.101.32}"

echo "📡 Connexion à ${SSH_HOST}..."
echo ""

ssh "$SSH_HOST" << 'ENDSSH'
    echo "✍️  Création d'un start.sh correct..."
    
    # Se déplacer dans le répertoire du projet
    cd /home/feustey/mcp-production || cd /home/feustey/MCP || cd ~/mcp || {
        echo "❌ Répertoire introuvable"
        exit 1
    }
    
    # Créer un start.sh correct
    cat > start.sh << 'EOF'
#!/bin/bash
#
# Script de démarrage pour MCP Docker
# Dernière mise à jour: 10 octobre 2025

set -e

echo "=========================================="
echo "Démarrage du système MCP"
echo "=========================================="
echo "Mode: ${ENVIRONMENT:-production}"
echo "Port: ${PORT:-8000}"
echo "Workers: ${WORKERS:-2}"
echo ""

# Vérifier les variables d'environnement essentielles
if [ -z "$MONGO_URL" ]; then
    echo "⚠️  WARNING: MONGO_URL non défini"
fi

echo "✅ Configuration chargée"
echo ""

# Définir les valeurs par défaut
PORT=${PORT:-8000}
WORKERS=${WORKERS:-2}
LOG_LEVEL=${LOG_LEVEL:-info}

# Chemin vers l'application
# Le Dockerfile copie le code dans /app, donc app.main:app est correct
APP_MODULE="app.main:app"

echo "🚀 Démarrage de Uvicorn..."
echo "   Module: $APP_MODULE"
echo "   Host: 0.0.0.0"
echo "   Port: $PORT"
echo "   Workers: $WORKERS"
echo "   Log level: $LOG_LEVEL"
echo ""

# Lancer l'application avec exec pour une bonne gestion des signaux
exec uvicorn "$APP_MODULE" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    --use-colors
EOF
    
    # Rendre le script exécutable
    chmod +x start.sh
    
    echo "✅ start.sh créé et rendu exécutable"
    echo ""
    
    # Copier le start.sh dans l'emplacement du Dockerfile
    mkdir -p scripts
    cp start.sh scripts/start.sh
    chmod +x scripts/start.sh
    
    echo "📦 Rebuild de l'image Docker..."
    docker-compose build mcp-api
    
    echo ""
    echo "🔄 Redémarrage du service..."
    docker-compose down mcp-api || true
    docker-compose up -d mcp-api
    
    echo ""
    echo "⏳ Attente 20 secondes..."
    sleep 20
    
    echo ""
    echo "📊 État du container:"
    docker-compose ps mcp-api
    
    echo ""
    echo "📄 Logs (20 dernières lignes):"
    docker-compose logs mcp-api --tail 20
    
    echo ""
    echo "🏥 Test healthcheck interne:"
    if docker exec mcp-api curl -f http://localhost:8000/health 2>/dev/null; then
        echo "✅ API répond correctement"
    else
        echo "⚠️  API ne répond pas encore"
    fi
ENDSSH

echo ""
echo "✅ Script terminé"


