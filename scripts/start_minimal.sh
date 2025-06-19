#!/bin/sh

# Script de démarrage minimal pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage minimal de MCP..."

# Variables d'environnement minimales avec valeurs par défaut
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"
export ENVIRONMENT="production"

# Variables requises avec valeurs par défaut
export AI_OPENAI_API_KEY="sk-dummy-key-for-testing"
export SECURITY_SECRET_KEY="dummy-secret-key-for-testing"

echo "✅ Configuration minimale appliquée"
echo "📍 URL: http://0.0.0.0:8000"

# Démarrage direct
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 