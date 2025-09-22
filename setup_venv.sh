#!/bin/bash

# Script d'installation des dépendances dans un environnement virtuel
# Pour MCP avec support Lightning Network

echo "🚀 Configuration de l'environnement virtuel MCP..."

# Détection du système d'exploitation
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo "📍 Système détecté: ${MACHINE}"

# Création de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
else
    echo "✅ Environnement virtuel déjà existant"
fi

# Activation de l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Mise à jour pip
echo "📥 Mise à jour de pip..."
pip install --upgrade pip

# Installation des dépendances critiques en premier
echo "⚡ Installation des dépendances critiques..."
pip install motor httpx requests

# Installation des dépendances complètes
echo "📦 Installation des dépendances depuis requirements.txt..."
pip install -r requirements.txt

# Vérification des installations
echo "✅ Vérification des installations..."
python3 -c "import motor; print('✓ motor installé')"
python3 -c "import httpx; print('✓ httpx installé')"
python3 -c "import requests; print('✓ requests installé')"
python3 -c "import fastapi; print('✓ fastapi installé')"
python3 -c "import redis; print('✓ redis installé')"
python3 -c "import jwt; print('✓ PyJWT installé')"

# Création d'un fichier .env.development si nécessaire
if [ ! -f ".env.development" ]; then
    echo "📝 Création du fichier .env.development..."
    cat > .env.development << EOF
# Environment de développement
DEVELOPMENT_MODE=true
JWT_SECRET_KEY=development_secret_key_min32characters
LNBITS_URL=http://localhost:5001
LNBITS_API_KEY=mock_api_key
LNBITS_ADMIN_KEY=mock_admin_key
MONGO_URL=mongodb://localhost:27017/mcp_dev
REDIS_URL=redis://localhost:6379
LOG_LEVEL=DEBUG
EOF
    echo "✅ Fichier .env.development créé"
fi

echo ""
echo "🎉 Installation terminée avec succès!"
echo ""
echo "Pour activer l'environnement virtuel:"
echo "  source venv/bin/activate"
echo ""
echo "Pour lancer l'application:"
echo "  python3 -m uvicorn main:app --reload"
echo ""
echo "Pour tester LNBits:"
echo "  python3 test_lnbits_minimal.py"