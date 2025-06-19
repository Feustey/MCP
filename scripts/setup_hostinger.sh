#!/bin/bash

# Script de configuration pour le serveur Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Configuration du serveur Hostinger pour MCP..."

# Vérification de Python
echo "📋 Vérification de Python..."
python3 --version
pip3 --version

# Mise à jour des paquets système
echo "🔄 Mise à jour des paquets système..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv build-essential

# Création d'un environnement virtuel
echo "🐍 Création de l'environnement virtuel..."
python3 -m venv /home/feustey/venv
source /home/feustey/venv/bin/activate

# Mise à jour de pip
echo "⬆️ Mise à jour de pip..."
pip install --upgrade pip setuptools wheel

# Installation des dépendances
echo "📦 Installation des dépendances..."
cd /home/feustey
pip install -r requirements.txt

# Configuration des permissions
echo "🔐 Configuration des permissions..."
chmod +x scripts/*.sh

# Création des répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p data/logs data/metrics data/reports rag/RAG_assets/nodes/simulations

# Configuration de l'environnement
echo "⚙️ Configuration de l'environnement..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Configuration MCP pour Hostinger
DRY_RUN=true
LOG_LEVEL=INFO
ENVIRONMENT=production

# Base de données (optionnel pour le MVP)
# MONGODB_URI=mongodb://localhost:27017/mcp
# REDIS_URL=redis://localhost:6379/0

# API Keys (à configurer selon vos besoins)
# OPENAI_API_KEY=your_openai_key_here

# Configuration des ports
API_PORT=80
API_HOST=0.0.0.0
EOF
    echo "✅ Fichier .env créé"
else
    echo "ℹ️ Fichier .env existe déjà"
fi

# Test de l'installation
echo "🧪 Test de l'installation..."
python3 -c "import fastapi, pydantic, uvicorn; print('✅ Toutes les dépendances sont installées')"

echo "🎉 Configuration terminée!"
echo ""
echo "📝 Pour démarrer l'application:"
echo "   source /home/feustey/venv/bin/activate"
echo "   cd /home/feustey"
echo "   uvicorn src.api.main:app --host 0.0.0.0 --port 80"
echo ""
echo "🔧 Pour un démarrage en arrière-plan:"
echo "   nohup uvicorn src.api.main:app --host 0.0.0.0 --port 80 > logs/app.log 2>&1 &" 