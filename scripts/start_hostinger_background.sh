#!/bin/bash

set -e

echo "🚀 Démarrage de MCP en arrière-plan sur Hostinger..."

# Vérification et configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."

# Configuration des clés API et sécurité
export OPENAI_API_KEY="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"
export SECRET_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY"

# Configuration MongoDB
export MONGO_URL="mongodb://localhost:27017"
export MONGO_DB_NAME="mcp"

# Activation de l'environnement virtuel
echo "🐍 Activation de l'environnement virtuel..."
source /home/feustey/venv/bin/activate

# Changement vers le répertoire de l'application
cd /home/feustey

# Création du répertoire de logs si nécessaire
mkdir -p logs

# Arrêt de l'application précédente si elle tourne
echo "🛑 Arrêt de l'application précédente..."
pkill -f "uvicorn src.api.main:app" || true
sleep 2

# Démarrage de l'application en arrière-plan
echo "🌐 Démarrage de l'API MCP en arrière-plan..."
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 80 > logs/app.log 2>&1 &

# Attendre un peu pour que l'application démarre
sleep 3

# Vérification du démarrage
if pgrep -f "uvicorn src.api.main:app" > /dev/null; then
    echo "✅ Application démarrée avec succès!"
    echo "📍 URL: http://$(hostname -I | awk '{print $1}'):80"
    echo "📊 Documentation: http://$(hostname -I | awk '{print $1}'):80/docs"
    echo "📋 Logs: tail -f logs/app.log"
    echo "🆔 PID: $(pgrep -f 'uvicorn src.api.main:app')"
else
    echo "❌ Échec du démarrage. Vérifiez les logs:"
    tail -n 20 logs/app.log
    exit 1
fi