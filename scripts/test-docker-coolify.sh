#!/bin/bash
# scripts/test-docker-coolify.sh - Test rapide de l'image Docker
# Dernière mise à jour: 27 mai 2025

set -e

echo "🧪 Test rapide Docker pour Coolify"
echo "=================================="

# Variables
IMAGE_NAME="mcp-coolify-test"
CONTAINER_NAME="mcp-test-quick"

# Nettoyage préalable
echo "🧹 Nettoyage préalable..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
docker rmi $IMAGE_NAME 2>/dev/null || true

# Construction de l'image
echo "🔨 Construction de l'image..."
docker build -f Dockerfile.coolify -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "❌ Échec de la construction"
    exit 1
fi
echo "✅ Image construite"

# Test rapide sans dépendances externes
echo "🚀 Démarrage du test (mode autonome)..."
docker run -d --name $CONTAINER_NAME -p 8000:8000 \
  -e ENVIRONMENT=test \
  -e LOG_LEVEL=DEBUG \
  -e DRY_RUN=true \
  -e AI_OPENAI_API_KEY=sk-test-key \
  -e SECURITY_SECRET_KEY=test-secret-key-for-testing-purposes \
  -e MONGO_URL=mongodb://localhost:27017/test \
  -e REDIS_HOST=localhost \
  -e REDIS_PORT=6379 \
  $IMAGE_NAME

# Attendre et tester
echo "⏳ Attente du démarrage (30s)..."
sleep 30

# Tests de santé
echo "🔍 Test de santé..."
if curl -f http://localhost:8000/health 2>/dev/null; then
    echo "✅ Health check réussi !"
    
    # Test de l'endpoint racine
    echo "🔍 Test endpoint racine..."
    RESPONSE=$(curl -s http://localhost:8000/ 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ Endpoint racine accessible"
        echo "📄 Réponse: $RESPONSE"
    else
        echo "⚠️  Endpoint racine non accessible"
    fi
    
    # Afficher les logs pour diagnostic
    echo "📋 Logs récents:"
    docker logs --tail 20 $CONTAINER_NAME
    
else
    echo "❌ Test échoué"
    echo "📋 Logs du conteneur:"
    docker logs $CONTAINER_NAME
    
    echo "📋 Informations du conteneur:"
    docker inspect $CONTAINER_NAME | grep -A 10 -B 10 "State"
fi

# Test avec curl verbeux pour plus d'infos
echo "🔍 Test détaillé..."
curl -v http://localhost:8000/health 2>&1 || true

# Nettoyage
echo "🧹 Nettoyage..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

echo ""
if curl -f http://localhost:8000/health &>/dev/null; then
    echo "✅ Test global réussi - Image prête pour Coolify !"
else
    echo "✅ Test terminé - Vérifiez les logs ci-dessus"
fi
echo "🔗 Prochaine étape: ./scripts/deploy-docker-coolify.sh" 