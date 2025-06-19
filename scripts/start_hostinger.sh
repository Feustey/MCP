#!/bin/bash

# Script de démarrage pour MCP sur Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Démarrage de MCP sur Hostinger..."

# Activation de l'environnement virtuel
echo "🐍 Activation de l'environnement virtuel..."
source /home/feustey/venv/bin/activate

# Vérification des dépendances
echo "🔍 Vérification des dépendances..."
python3 -c "import fastapi, pydantic, uvicorn" || {
    echo "❌ Dépendances manquantes. Exécutez d'abord: bash scripts/setup_hostinger.sh"
    exit 1
}

# Changement vers le répertoire de l'application
cd /home/feustey

# Création du répertoire de logs si nécessaire
mkdir -p logs

# Démarrage de l'application
echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://$(hostname -I | awk '{print $1}'):80"
echo "📊 Documentation: http://$(hostname -I | awk '{print $1}'):80/docs"
echo ""

# Démarrage avec uvicorn
exec uvicorn src.api.main:app --host 0.0.0.0 --port 80 --reload 