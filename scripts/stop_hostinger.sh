#!/bin/bash

# Script d'arrêt pour MCP sur Hostinger
# Dernière mise à jour: 9 mai 2025

echo "🛑 Arrêt de MCP sur Hostinger..."

# Recherche et arrêt du processus uvicorn
PID=$(pgrep -f "uvicorn src.api.main:app")

if [ -n "$PID" ]; then
    echo "📋 Processus trouvé avec PID: $PID"
    echo "🔄 Arrêt en cours..."
    kill $PID
    
    # Attendre l'arrêt
    sleep 3
    
    # Vérifier si le processus est toujours en cours
    if pgrep -f "uvicorn src.api.main:app" > /dev/null; then
        echo "⚠️ Arrêt forcé nécessaire..."
        pkill -9 -f "uvicorn src.api.main:app"
        sleep 1
    fi
    
    echo "✅ Application arrêtée avec succès!"
else
    echo "ℹ️ Aucune application MCP en cours d'exécution"
fi

# Affichage des processus Python en cours
echo ""
echo "📋 Processus Python en cours:"
ps aux | grep python | grep -v grep || echo "Aucun processus Python trouvé" 