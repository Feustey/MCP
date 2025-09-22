#!/bin/bash

set -e

echo "🚀 Build et déploiement production MCP"

# Arrêt des services
echo "⏹️ Arrêt des services..."
docker compose -f docker-compose.production.yml down

# Nettoyage
echo "🧹 Nettoyage Docker..."
docker system prune -f
docker volume prune -f

# Construction de l'image avec le code actuel
echo "🔨 Construction image production..."
docker build -f Dockerfile.simple -t feustey/mcp-dazno:production-2024 .

# Mise à jour du docker-compose pour utiliser la nouvelle image
sed -i 's/image: feustey\/mcp-dazno:fixed-amd64/image: feustey\/mcp-dazno:production-2024/' docker-compose.production.yml

# Simplification des volumes (enlever les montages source)
sed -i '/- \.\/src:\/app\/src:ro/d' docker-compose.production.yml
sed -i '/- \.\/app:\/app\/app:ro/d' docker-compose.production.yml
sed -i '/- \.\/config\.py:\/app\/config\.py:ro/d' docker-compose.production.yml
sed -i '/- \.\/scripts\/simple_entrypoint\.sh:\/app\/scripts\/simple_entrypoint\.sh:ro/d' docker-compose.production.yml

# Simplification de la commande
sed -i 's/command: \["bash", "\/app\/scripts\/simple_entrypoint\.sh"\]/command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]/' docker-compose.production.yml

# Redémarrage
echo "🚀 Redémarrage des services..."
docker compose -f docker-compose.production.yml up -d

echo "✅ Déploiement terminé!"
echo "⏱️ Attendre 60s pour stabilisation..."
sleep 60

# Tests
echo "🧪 Tests des endpoints..."
curl -s http://localhost:8000/api/v1/health && echo " ✅ API Health OK" || echo " ❌ API Health Failed"
curl -s http://localhost:8000/api/v1/rag/health && echo " ✅ RAG OK" || echo " ❌ RAG Failed"  
curl -s http://localhost:8000/api/v1/lightning/health && echo " ✅ Lightning OK" || echo " ❌ Lightning Failed"

echo "🎉 Déploiement production terminé!"