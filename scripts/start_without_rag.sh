#!/bin/sh

# Script de démarrage sans RAG pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage MCP sans RAG..."

# Création des répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p logs data rag backups

# Configuration des variables d'environnement
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"
export ENVIRONMENT="production"

# Variables requises avec valeurs par défaut
export AI_OPENAI_API_KEY="sk-dummy-key-for-testing"
export SECURITY_SECRET_KEY="dummy-secret-key-for-testing"

# Désactiver le logging vers fichier en mode conteneur
export LOG_ENABLE_FILE_LOGGING="false"
export LOG_LEVEL="INFO"
export LOG_FORMAT="text"

# Désactiver les fonctionnalités RAG
export DISABLE_RAG="true"

echo "✅ Configuration sans RAG appliquée"
echo "📍 URL: http://0.0.0.0:8000"
echo "ℹ️ Les fonctionnalités RAG ne sont pas disponibles"

# Démarrage direct
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 