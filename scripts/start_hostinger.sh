#!/bin/bash

set -e

echo "🚀 Démarrage de MCP sur Hostinger..."

# Vérification et configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."

# Configuration des clés API
export AI_OPENAI_API_KEY="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"
export SECURITY_SECRET_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY"

# Activation de l'environnement virtuel
echo "🐍 Activation de l'environnement virtuel..."
source /home/feustey/venv/bin/activate

# Changement vers le répertoire de l'application
cd /home/feustey

# Création du répertoire de logs si nécessaire
mkdir -p logs

# Démarrage de l'application
echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://$(hostname -I | awk '{print $1}'):8000"
echo "📊 Documentation: http://$(hostname -I | awk '{print $1}'):8000/docs"

# Démarrage avec uvicorn
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000