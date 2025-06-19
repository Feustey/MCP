#!/bin/sh

# Script de démarrage robuste pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage robuste de MCP..."

# Fonction de nettoyage
cleanup() {
    echo "🧹 Nettoyage en cours..."
    pkill -f "uvicorn.*src.api.main" 2>/dev/null || true
    exit 0
}

# Capture des signaux
trap cleanup INT TERM

# Création des répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p logs data rag backups

# Configuration des variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."
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

# Désactiver complètement les fonctionnalités RAG
export DISABLE_RAG="true"
export RAG_AVAILABLE="false"

echo "✅ Configuration appliquée"

# Vérification des dépendances
echo "🔍 Vérification des dépendances..."
python3 -c "import fastapi, uvicorn, pymongo, redis" 2>/dev/null || {
    echo "❌ Dépendances manquantes, installation..."
    pip install -r requirements-hostinger.txt
}

# Test d'import de l'application
echo "🧪 Test d'import de l'application..."
python3 -c "from src.api.main import app; print('✅ Application importée avec succès')" || {
    echo "❌ Erreur d'import de l'application"
    echo "🔍 Exécution du diagnostic..."
    sh scripts/diagnose.sh
    exit 1
}

echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"
echo "🔄 Mode robuste avec redémarrage automatique"

# Boucle de redémarrage automatique
while true; do
    echo "🚀 Démarrage de l'application..."
    
    # Démarrage avec uvicorn et gestion d'erreurs
    uvicorn src.api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        --access-log \
        --timeout-keep-alive 30 \
        --limit-concurrency 1000 \
        --limit-max-requests 10000
    
    exit_code=$?
    
    echo "⚠️ Application arrêtée avec le code: $exit_code"
    
    # Attendre avant de redémarrer
    echo "⏳ Redémarrage dans 5 secondes..."
    sleep 5
done 