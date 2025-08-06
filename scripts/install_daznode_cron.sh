#!/bin/bash

# Script pour installer la tâche cron du rapport quotidien Daznode
# Usage: ./scripts/install_daznode_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CRON_FILE="$SCRIPT_DIR/crontab_daznode_report.txt"
LOG_DIR="$PROJECT_ROOT/logs"

echo "🔧 Configuration du rapport quotidien Daznode..."

# Créer le répertoire de logs s'il n'existe pas
if [ ! -d "$LOG_DIR" ]; then
    echo "📁 Création du répertoire de logs: $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi

# Rendre le script exécutable
echo "🔐 Configuration des permissions du script..."
chmod +x "$SCRIPT_DIR/daily_daznode_report.py"

# Vérifier si le fichier crontab existe
if [ ! -f "$CRON_FILE" ]; then
    echo "❌ Erreur: Fichier crontab non trouvé: $CRON_FILE"
    exit 1
fi

echo "📋 Ajout des tâches cron..."

# Sauvegarder le crontab actuel
crontab -l > /tmp/current_crontab 2>/dev/null || echo "# Nouveau crontab" > /tmp/current_crontab

# Vérifier si la tâche existe déjà
if grep -q "daily_daznode_report.py" /tmp/current_crontab; then
    echo "⚠️  La tâche cron existe déjà. Suppression de l'ancienne version..."
    grep -v "daily_daznode_report.py" /tmp/current_crontab > /tmp/new_crontab
    mv /tmp/new_crontab /tmp/current_crontab
fi

# Ajouter les nouvelles tâches
echo "" >> /tmp/current_crontab
echo "# Tâches automatisées Daznode MCP" >> /tmp/current_crontab
cat "$CRON_FILE" >> /tmp/current_crontab

# Installer le nouveau crontab
crontab /tmp/current_crontab

# Nettoyer
rm -f /tmp/current_crontab

echo "✅ Configuration terminée!"
echo ""
echo "📊 Rapport quotidien Daznode configuré pour 7h00 tous les jours"
echo "📝 Logs disponibles dans: $LOG_DIR/daznode_report.log"
echo ""
echo "🔍 Pour vérifier l'installation:"
echo "   crontab -l | grep daznode"
echo ""
echo "🧪 Pour tester le script manuellement:"
echo "   cd $PROJECT_ROOT && python3 scripts/daily_daznode_report.py"
echo ""
echo "⚠️  Assurez-vous que les variables d'environnement suivantes sont définies:"
echo "   - TELEGRAM_BOT_TOKEN"
echo "   - TELEGRAM_CHAT_ID"
echo "   - FEUSTEY_NODE_ID (optionnel, valeur par défaut fournie)"
echo "   - LNBITS_URL (optionnel, par défaut: http://127.0.0.1:5000)"
echo "   - LNBITS_API_KEY"