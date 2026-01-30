#!/bin/bash
#
# Script de démarrage pour MCP Docker (Hostinger / production)
# Dernière mise à jour: 30 janvier 2025

set -e

echo "=========================================="
echo "Démarrage du système MCP"
echo "=========================================="
echo "Mode: ${ENVIRONMENT:-production}"
echo "Port: ${PORT:-8000}"
echo "Workers: ${WORKERS:-2}"
echo ""

# Vérifier les variables d'environnement essentielles
if [ -z "$MONGO_URL" ] && [ -z "$MONGODB_URL" ]; then
    echo "⚠️  WARNING: MONGO_URL / MONGODB_URL non défini"
fi

echo "✅ Configuration chargée"
echo ""

# Définir les valeurs par défaut (PORT pour Runway / plateformes cloud)
PORT=${PORT:-8000}
WORKERS=${WORKERS:-2}
LOG_LEVEL=${LOG_LEVEL:-info}

# Chemin vers l'application
APP_MODULE="app.main:app"

echo "🚀 Démarrage de Uvicorn..."
echo "   Module: $APP_MODULE"
echo "   Host: 0.0.0.0"
echo "   Port: $PORT"
echo "   Workers: $WORKERS"
echo "   Log level: $LOG_LEVEL"
echo ""

# Lancer l'application avec exec pour une bonne gestion des signaux
exec uvicorn "$APP_MODULE" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    --use-colors
