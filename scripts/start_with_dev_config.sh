#!/bin/sh

# Script de démarrage avec configuration de développement
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage MCP avec configuration de développement..."

# Sauvegarde de l'ancien fichier config
if [ -f "config.py" ]; then
    echo "💾 Sauvegarde de config.py..."
    cp config.py config.py.backup
fi

# Remplacement temporaire par la config de développement
if [ -f "config_dev.py" ]; then
    echo "🔄 Utilisation de la configuration de développement..."
    cp config_dev.py config.py
else
    echo "❌ Fichier config_dev.py non trouvé"
    exit 1
fi

# Configuration des variables d'environnement
export ENVIRONMENT="development"
export DEBUG="true"
export DRY_RUN="true"

# Variables principales (Hostinger)
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"

# Variables avec valeurs par défaut
export AI_OPENAI_API_KEY="sk-dummy-key-for-testing"
export SECURITY_SECRET_KEY="dummy-secret-key-for-testing"

echo "✅ Configuration appliquée"
echo "📍 URL: http://0.0.0.0:8000"

# Fonction de nettoyage
cleanup() {
    echo "🧹 Restauration de la configuration originale..."
    if [ -f "config.py.backup" ]; then
        mv config.py.backup config.py
    fi
}

# Capture du signal d'interruption
trap cleanup INT TERM

# Démarrage de l'application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 