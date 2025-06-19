#!/bin/bash

# Script de vérification du statut pour MCP sur Hostinger
# Dernière mise à jour: 9 mai 2025

echo "📊 Statut de MCP sur Hostinger"
echo "================================"

# Vérification du processus
PID=$(pgrep -f "uvicorn src.api.main:app")

if [ -n "$PID" ]; then
    echo "✅ Application en cours d'exécution"
    echo "🆔 PID: $PID"
    echo "⏰ Démarrage: $(ps -o lstart= -p $PID)"
    echo "💾 Mémoire: $(ps -o rss= -p $PID | awk '{print $1/1024 " MB"}')"
    echo "🖥️ CPU: $(ps -o %cpu= -p $PID)%"
else
    echo "❌ Application non démarrée"
fi

echo ""

# Vérification de l'environnement virtuel
if [ -d "/home/feustey/venv" ]; then
    echo "🐍 Environnement virtuel: ✅ Présent"
else
    echo "🐍 Environnement virtuel: ❌ Absent"
fi

# Vérification des dépendances
echo ""
echo "📦 Vérification des dépendances..."
source /home/feustey/venv/bin/activate 2>/dev/null && {
    python3 -c "import fastapi, pydantic, uvicorn; print('✅ Dépendances installées')" 2>/dev/null || {
        echo "❌ Dépendances manquantes"
    }
} || {
    echo "❌ Impossible d'activer l'environnement virtuel"
}

# Vérification des ports
echo ""
echo "🌐 Vérification des ports..."
if netstat -tlnp 2>/dev/null | grep :8000 > /dev/null; then
    echo "✅ Port 8000: En écoute"
    netstat -tlnp 2>/dev/null | grep :8000
else
    echo "❌ Port 8000: Non en écoute"
fi

# Vérification de la configuration
echo ""
echo "⚙️ Vérification de la configuration..."
if [ -f "/home/feustey/.env" ]; then
    echo "✅ Fichier .env: Présent"
    echo "📋 Variables principales:"
    grep -E "^(MONGO_URL|REDIS_HOST|ENVIRONMENT|DRY_RUN)=" /home/feustey/.env | head -5
else
    echo "❌ Fichier .env: Absent"
fi

# Vérification des logs récents
echo ""
echo "📋 Logs récents (dernières 10 lignes):"
if [ -f "/home/feustey/logs/app.log" ]; then
    tail -n 10 /home/feustey/logs/app.log
else
    echo "Aucun fichier de log trouvé"
fi

# Test de connectivité API
echo ""
echo "🔗 Test de connectivité API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API accessible localement"
    echo "📊 Réponse health check:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "❌ API non accessible localement"
fi 