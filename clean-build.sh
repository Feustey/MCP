#!/bin/bash

echo "🔄 Passage à Python 3.12 (si installé)"
pyenv install 3.12.2
pyenv local 3.12.2
python --version

echo "🔄 Upgrade de pip, setuptools et wheel"
pip install --upgrade pip setuptools wheel

echo "🟣 Installation de pip-tools"
pip install pip-tools

echo "🟣 Nettoyage de l'environnement"
rm -rf .venv
python -m venv .venv
source .venv/bin/activate

echo "🟣 Recréation des requirements"
# Liste manuelle de tes dépendances de base
cat > requirements.in << EOF
fastapi
uvicorn
python-dotenv
aiohttp
redis
openai
numpy
pydantic
python-jose[cryptography]
passlib[bcrypt]
python-multipart
slowapi
EOF

# Compile un requirements.txt propre
pip-compile --upgrade

echo "✅ Installation des dépendances nettoyées"
pip install -r requirements.txt

echo "🎉 Fait ! Tu peux maintenant tester ton app"
