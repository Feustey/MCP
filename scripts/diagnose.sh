#!/bin/sh

# Script de diagnostic pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🔍 Diagnostic MCP..."

# Vérification de l'environnement
echo "📋 Vérification de l'environnement..."
echo "Python version: $(python3 --version)"
echo "Pip version: $(pip --version)"
echo "Répertoire courant: $(pwd)"
echo "Contenu du répertoire:"
ls -la

# Vérification des dépendances
echo ""
echo "📦 Vérification des dépendances..."
python3 -c "import fastapi, uvicorn, pymongo, redis; print('✅ Dépendances de base OK')" || {
    echo "❌ Dépendances de base manquantes"
    echo "Installation..."
    pip install -r requirements-hostinger.txt
}

# Vérification des fichiers de configuration
echo ""
echo "⚙️ Vérification des fichiers de configuration..."
if [ -f "config.py" ]; then
    echo "✅ config.py présent"
else
    echo "❌ config.py manquant"
fi

if [ -f "src/api/main.py" ]; then
    echo "✅ src/api/main.py présent"
else
    echo "❌ src/api/main.py manquant"
fi

# Test de configuration
echo ""
echo "🧪 Test de configuration..."
python3 -c "
import os
print('Variables d\'environnement:')
for var in ['MONGO_URL', 'REDIS_HOST', 'ENVIRONMENT', 'AI_OPENAI_API_KEY', 'SECURITY_SECRET_KEY']:
    value = os.getenv(var)
    if value:
        print(f'  {var}: {value[:50]}{"..." if len(value) > 50 else ""}')
    else:
        print(f'  {var}: NON DÉFINIE')
"

# Test d'import de l'application
echo ""
echo "🔧 Test d'import de l'application..."
python3 -c "
try:
    from src.api.main import app
    print('✅ Application FastAPI importée avec succès')
except Exception as e:
    print(f'❌ Erreur d\'import: {e}')
    import traceback
    traceback.print_exc()
"

# Test de démarrage rapide
echo ""
echo "🚀 Test de démarrage rapide..."
timeout 10s python3 -c "
import uvicorn
from src.api.main import app
print('Démarrage du serveur de test...')
uvicorn.run(app, host='127.0.0.1', port=8001, log_level='error')
" || echo "⚠️ Test de démarrage interrompu (normal)"

echo ""
echo "✅ Diagnostic terminé" 