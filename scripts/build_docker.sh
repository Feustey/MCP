#!/bin/bash

# Script de construction Docker pour MCP
# Dernière mise à jour: 9 mai 2025

set -e

echo "🐳 Construction de l'image Docker MCP..."

# Variables
IMAGE_NAME="mcp-api"
TAG="latest"
DOCKERFILE="Dockerfile.production"

# Vérification de la présence du fichier requirements-hostinger.txt
if [ ! -f "requirements-hostinger.txt" ]; then
    echo "❌ Fichier requirements-hostinger.txt manquant"
    exit 1
fi

# Construction de l'image
echo "🔨 Construction de l'image $IMAGE_NAME:$TAG..."
docker build -f $DOCKERFILE -t $IMAGE_NAME:$TAG .

# Vérification de la construction
if [ $? -eq 0 ]; then
    echo "✅ Image construite avec succès!"
    echo "📋 Informations de l'image:"
    docker images $IMAGE_NAME:$TAG
    
    echo ""
    echo "🚀 Pour démarrer le conteneur:"
    echo "   docker run -p 8000:8000 $IMAGE_NAME:$TAG"
    echo ""
    echo "🔧 Ou avec docker-compose:"
    echo "   docker-compose up -d"
else
    echo "❌ Échec de la construction"
    exit 1
fi 