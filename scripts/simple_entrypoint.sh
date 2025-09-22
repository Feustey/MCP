#!/bin/bash

# Script d'entrée simplifié pour l'API MCP en production
echo "🚀 Démarrage API MCP Production Simple"

# Variables d'environnement
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export PYTHONPATH=/app:/app/src
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Création des dossiers nécessaires
mkdir -p /app/logs /app/data /app/rag /app/backups /app/reports

echo "📁 Dossiers créés"
echo "🔧 Variables d'environnement configurées"
echo "🐍 PYTHONPATH: $PYTHONPATH"

# Vérification des fichiers critiques
if [[ ! -f "/app/app/main.py" ]]; then
    echo "❌ Fichier app/main.py manquant"
    exit 1
fi

if [[ ! -d "/app/src" ]]; then
    echo "❌ Dossier src manquant"
    exit 1
fi

echo "✅ Fichiers critiques présents"

# Test d'import rapide
cd /app
python -c "import app.main" 2>/dev/null && echo "✅ Import app.main OK" || echo "❌ Erreur import app.main"

# Lancement de l'API
echo "🚀 Lancement uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info