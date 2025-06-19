#!/bin/bash

# Script de démarrage Docker pour MCP
# Dernière mise à jour: 9 mai 2025

set -e

echo "🐳 Démarrage de MCP avec Docker..."

# Vérification de Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé"
    exit 1
fi

# Configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."
bash scripts/configure_docker_env.sh

# Construction de l'image si nécessaire
echo "🔨 Vérification de l'image Docker..."
if [[ "$(docker images -q mcp-api:latest 2> /dev/null)" == "" ]]; then
    echo "📦 Construction de l'image..."
    bash scripts/build_docker.sh
else
    echo "✅ Image déjà construite"
fi

# Arrêt des conteneurs existants
echo "🛑 Arrêt des conteneurs existants..."
docker-compose down 2>/dev/null || true
docker stop mcp-api 2>/dev/null || true
docker rm mcp-api 2>/dev/null || true

# Démarrage avec Docker Compose
echo "🚀 Démarrage avec Docker Compose..."
docker-compose --env-file .env.docker up -d

# Attendre que le service démarre
echo "⏳ Attente du démarrage..."
sleep 5

# Vérification du statut
echo "📊 Vérification du statut..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Application démarrée avec succès!"
    echo "📍 URL: http://localhost:8000"
    echo "📊 Documentation: http://localhost:8000/docs"
    echo "🔍 Health check: http://localhost:8000/health"
    echo ""
    echo "📋 Logs:"
    echo "   docker-compose logs -f mcp-api"
    echo ""
    echo "🛑 Arrêt:"
    echo "   docker-compose down"
else
    echo "❌ Échec du démarrage"
    echo "📋 Logs d'erreur:"
    docker-compose logs mcp-api
    exit 1
fi 