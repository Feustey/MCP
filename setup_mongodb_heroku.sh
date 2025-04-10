#!/bin/bash

echo "🚀 Configuration de MongoDB pour Heroku"

# Vérifier si l'addon MongoDB est déjà installé
MONGO_ADDON=$(heroku addons | grep -i "mongodb")

if [ -z "$MONGO_ADDON" ]; then
  echo "⚙️ Installation de l'addon MongoDB Atlas..."
  heroku addons:create mongolab:sandbox
  echo "✅ MongoDB Atlas installé"
else
  echo "✅ MongoDB Atlas déjà installé"
fi

# Récupérer l'URL MongoDB
MONGODB_URI=$(heroku config:get MONGODB_URI)

if [ -z "$MONGODB_URI" ]; then
  echo "❌ Erreur: Impossible de récupérer l'URL MongoDB"
  exit 1
fi

echo "✅ URL MongoDB configurée: $MONGODB_URI"

# Vérifier la connexion à MongoDB
echo "⚙️ Test de connexion à MongoDB..."
python -c "
from pymongo import MongoClient
import os

# Connexion à MongoDB
uri = '$MONGODB_URI'
client = MongoClient(uri)

# Test de la connexion
client.admin.command('ping')

print('✅ Connexion à MongoDB réussie!')
"

echo "🎉 Configuration MongoDB terminée!" 