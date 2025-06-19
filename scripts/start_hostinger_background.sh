#!/bin/bash

# Script de démarrage en arrière-plan pour MCP sur Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Démarrage de MCP en arrière-plan sur Hostinger..."

# Activation de l'environnement virtuel
echo "🐍 Activation de l'environnement virtuel..."
source /home/feustey/venv/bin/activate

# Vérification des dépendances
echo "🔍 Vérification des dépendances..."
python3 -c "import fastapi, pydantic, uvicorn" || {
    echo "❌ Dépendances manquantes. Exécutez d'abord: bash scripts/setup_hostinger.sh"
    exit 1
}

# Changement vers le répertoire de l'application
cd /home/feustey

# Création du répertoire de logs si nécessaire
mkdir -p logs

# Vérification de la configuration
echo "⚙️ Vérification de la configuration..."
if [ ! -f .env ]; then
    echo "⚠️ Fichier .env manquant. Configuration automatique..."
    bash scripts/configure_hostinger_db.sh
fi

# Arrêt de l'application précédente si elle tourne
echo "🛑 Arrêt de l'application précédente..."
pkill -f "uvicorn src.api.main:app" || true
sleep 2

# Démarrage de l'application en arrière-plan
echo "🌐 Démarrage de l'API MCP en arrière-plan..."
nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &

# Attendre un peu pour que l'application démarre
sleep 3

# Vérification du démarrage
if pgrep -f "uvicorn src.api.main:app" > /dev/null; then
    echo "✅ Application démarrée avec succès!"
    echo "📍 URL: http://$(hostname -I | awk '{print $1}'):8000"
    echo "📊 Documentation: http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo "📋 Logs: tail -f logs/app.log"
    echo "🆔 PID: $(pgrep -f 'uvicorn src.api.main:app')"
else
    echo "❌ Échec du démarrage. Vérifiez les logs:"
    tail -n 20 logs/app.log
    exit 1
fi 