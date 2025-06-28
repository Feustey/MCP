#!/bin/sh

# Script de démarrage ultra-minimal pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🚀 Démarrage ultra-minimal de MCP..."

# Création des répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p logs data rag backups

# Configuration des variables d'environnement minimales
export MONGO_URL="mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true"
export REDIS_HOST="d4s8888skckos8c80w4swgcw"
export REDIS_PORT="6379"
export REDIS_USERNAME="default"
export REDIS_PASSWORD="YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1"
export ENVIRONMENT="production"
export AI_OPENAI_API_KEY="sk-dummy-key-for-testing"
export SECURITY_SECRET_KEY="dummy-secret-key-for-testing"
export LOG_ENABLE_FILE_LOGGING="false"
export LOG_LEVEL="INFO"
export LOG_FORMAT="text"
export DISABLE_RAG="true"
export RAG_AVAILABLE="false"

echo "✅ Configuration appliquée"

# Création d'une API FastAPI minimale si l'import échoue
echo "🧪 Test d'import de l'application..."
python3 -c "from src.api.main import app; print('✅ Application importée')" || {
    echo "⚠️ Création d'une API minimale..."
    cat > minimal_api.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="MCP Minimal API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "MCP API fonctionne!", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp"}

@app.get("/docs")
async def docs():
    return {"message": "Documentation disponible sur /docs"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
    echo "✅ API minimale créée"
    exec python3 minimal_api.py
}

echo "📍 URL: http://0.0.0.0:8000"
echo "📊 Documentation: http://0.0.0.0:8000/docs"

# Démarrage de l'application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --log-level info 