#!/bin/sh

# Script de vérification de santé pour MCP
# Dernière mise à jour: 9 mai 2025

echo "🏥 Vérification de santé MCP..."

# Vérification des processus
echo "📊 Vérification des processus..."
ps aux | grep -E "(uvicorn|python.*main)" | grep -v grep || {
    echo "❌ Aucun processus FastAPI en cours d'exécution"
}

# Vérification des ports
echo ""
echo "🔌 Vérification des ports..."
netstat -tlnp 2>/dev/null | grep :8000 || {
    echo "❌ Aucun service sur le port 8000"
}

# Test de connexion locale
echo ""
echo "🌐 Test de connexion locale..."
curl -s -o /dev/null -w "Code: %{http_code}, Temps: %{time_total}s\n" http://localhost:8000/health || {
    echo "❌ Impossible de se connecter à l'application locale"
}

# Test de connexion externe
echo ""
echo "🌍 Test de connexion externe..."
curl -s -o /dev/null -w "Code: %{http_code}, Temps: %{time_total}s\n" http://0.0.0.0:8000/health || {
    echo "❌ Impossible de se connecter à l'application externe"
}

# Vérification des logs
echo ""
echo "📝 Vérification des logs..."
if [ -f "logs/mcp.log" ]; then
    echo "Dernières lignes du log:"
    tail -10 logs/mcp.log
else
    echo "❌ Fichier de log non trouvé"
fi

# Vérification de la mémoire
echo ""
echo "💾 Vérification de la mémoire..."
free -h

# Vérification de l'espace disque
echo ""
echo "💿 Vérification de l'espace disque..."
df -h

# Test de démarrage rapide
echo ""
echo "🚀 Test de démarrage rapide..."
timeout 15s python3 -c "
import uvicorn
from src.api.main import app
print('Démarrage du serveur de test...')
uvicorn.run(app, host='127.0.0.1', port=8002, log_level='error')
" &
TEST_PID=$!

sleep 5

# Test du serveur de test
curl -s -o /dev/null -w "Test serveur - Code: %{http_code}\n" http://127.0.0.1:8002/health || {
    echo "❌ Le serveur de test ne répond pas"
}

# Arrêt du serveur de test
kill $TEST_PID 2>/dev/null || true

echo ""
echo "✅ Vérification de santé terminée" 