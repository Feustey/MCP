#!/bin/bash

echo "🔍 Test de la connexion MongoDB..."

# Charger les variables depuis .env.production
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

# Test avec mongosh
if command -v mongosh &> /dev/null; then
    if mongosh "$MONGODB_URI" --eval "db.adminCommand('ping')" &> /dev/null; then
        echo "✅ Connexion MongoDB réussie"
        exit 0
    else
        echo "❌ Échec de la connexion MongoDB"
        exit 1
    fi
else
    echo "❌ mongosh non installé"
    echo "📦 Installation avec : brew install mongosh"
    exit 1
fi
