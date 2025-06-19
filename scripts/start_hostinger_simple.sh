#!/bin/bash

# Script de démarrage pour MCP simplifié sur Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Démarrage de MCP simplifié sur Hostinger..."

# Activation de l'environnement virtuel
echo "🐍 Activation de l'environnement virtuel..."
source /home/feustey/venv/bin/activate

# Vérification des dépendances de base
echo "🔍 Vérification des dépendances..."
python3 -c "import fastapi, pydantic, uvicorn" || {
    echo "❌ Dépendances manquantes. Exécutez d'abord: bash scripts/setup_hostinger.sh"
    exit 1
}

# Changement vers le répertoire de l'application
cd /home/feustey

# Création du répertoire de logs si nécessaire
mkdir -p logs

# Démarrage de l'application simplifiée
echo "🌐 Démarrage de l'API MCP simplifiée..."
echo "📍 URL: http://$(hostname -I | awk '{print $1}'):8000"
echo "📊 Documentation: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""

# Démarrage avec uvicorn (version simplifiée)
exec uvicorn src.api.main_simple:app --host 0.0.0.0 --port 8000 --reload 