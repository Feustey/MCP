#!/bin/bash

echo "🔍 Vérification des variables d'environnement..."

# Liste des variables requises
required_vars=(
    "PORT"
    "MONGODB_URI"
    "OPENAI_API_KEY"
    "SPARKSEER_API_KEY"
    "AMBOSS_API_KEY"
    "LNBITS_API_KEY"
    "ENVIRONMENT"
)

# Charger les variables depuis .env.production
if [ -f .env.production ]; then
    set -a
    source .env.production
    set +a
else
    echo "❌ Fichier .env.production non trouvé"
    exit 1
fi

# Vérifier chaque variable
missing_vars=0
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ $var manquante"
        missing_vars=$((missing_vars + 1))
    else
        # Masquer les valeurs sensibles
        if [[ "$var" == *"KEY"* || "$var" == *"URI"* ]]; then
            echo "✅ $var configurée (valeur masquée)"
        else
            echo "✅ $var = ${!var}"
        fi
    fi
done

if [ $missing_vars -eq 0 ]; then
    echo "✨ Toutes les variables d'environnement sont configurées"
    
    # Test de connexion MongoDB
    echo "🔄 Test de la connexion MongoDB..."
    if command -v mongosh &> /dev/null; then
        if mongosh "$MONGODB_URI" --eval "db.adminCommand('ping')" &> /dev/null; then
            echo "✅ Connexion MongoDB réussie"
        else
            echo "❌ Échec de la connexion MongoDB"
            exit 1
        fi
    else
        echo "⚠️ mongosh non installé (optionnel)"
    fi
    
    exit 0
else
    echo "❌ $missing_vars variables manquantes"
    exit 1
fi