#!/bin/bash

# Script de démarrage pour conteneur Docker MCP
# Dernière mise à jour: 7 janvier 2025

set -e

echo "🚀 Démarrage de MCP dans le conteneur Docker..."

# Vérification des variables d'environnement critiques
echo "🔍 Vérification des variables d'environnement..."

# Variables obligatoires
required_vars=(
    "MONGO_URL"
    "REDIS_HOST"
    "REDIS_PASSWORD"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Variable d'environnement manquante: $var"
        exit 1
    fi
done

echo "✅ Variables d'environnement vérifiées"

# Création des répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p /app/logs /app/data /app/rag/RAG_assets

# Vérification des dépendances Python
echo "🐍 Vérification des dépendances Python..."
python3 -c "import fastapi, pydantic, uvicorn, pymongo, redis" || {
    echo "❌ Dépendances Python manquantes"
    exit 1
}

# Test de connectivité MongoDB
echo "🗄️ Test de connectivité MongoDB..."
python3 -c "
import pymongo
from pymongo import MongoClient
try:
    client = MongoClient('$MONGO_URL', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ MongoDB: Connexion réussie')
except Exception as e:
    print(f'❌ MongoDB: Erreur de connexion - {e}')
    exit(1)
" || {
    echo "⚠️ Attention: Impossible de se connecter à MongoDB"
}

# Test de connectivité Redis
echo "🔴 Test de connectivité Redis..."
python3 -c "
import redis
try:
    r = redis.Redis(
        host='$REDIS_HOST',
        port=int('$REDIS_PORT'),
        password='$REDIS_PASSWORD',
        ssl=True,
        socket_timeout=5
    )
    r.ping()
    print('✅ Redis: Connexion réussie')
except Exception as e:
    print(f'❌ Redis: Erreur de connexion - {e}')
    exit(1)
" || {
    echo "⚠️ Attention: Impossible de se connecter à Redis"
}

# Configuration du logging
echo "📋 Configuration du logging..."
export PYTHONPATH="/app:$PYTHONPATH"

# Démarrage de l'application
echo "🌐 Démarrage de l'API MCP..."
echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"
echo "🔍 Health check: http://0.0.0.0:8000/health"
echo ""

# Exécution de la commande passée en argument ou commande par défaut
if [ $# -eq 0 ]; then
    echo "🚀 Démarrage avec uvicorn par défaut..."
    exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    echo "🚀 Démarrage avec commande personnalisée: $@"
    exec "$@"
fi 