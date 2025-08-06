#!/bin/bash

# Script pour installer les tâches cron des rapports quotidiens MCP
# - Rapport Daznode (nœud Lightning) à 7h00
# - Rapport de santé de l'application à 7h05
# Usage: ./scripts/install_daily_reports_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"

echo "🔧 Configuration des rapports quotidiens MCP..."

# Créer le répertoire de logs s'il n'existe pas
if [ ! -d "$LOG_DIR" ]; then
    echo "📁 Création du répertoire de logs: $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi

# Rendre les scripts exécutables
echo "🔐 Configuration des permissions des scripts..."
chmod +x "$SCRIPT_DIR/daily_daznode_report.py"
chmod +x "$SCRIPT_DIR/daily_app_health_report.py"
chmod +x "$SCRIPT_DIR/test_daznode_report.py"
chmod +x "$SCRIPT_DIR/test_app_health_report.py"

echo "📋 Configuration des tâches cron..."

# Sauvegarder le crontab actuel
crontab -l > /tmp/current_crontab 2>/dev/null || echo "# Nouveau crontab MCP" > /tmp/current_crontab

# Supprimer les anciennes tâches MCP si elles existent
echo "🧹 Suppression des anciennes tâches MCP..."
grep -v "daily_daznode_report.py\|daily_app_health_report.py\|# Rapports quotidiens MCP" /tmp/current_crontab > /tmp/new_crontab || cp /tmp/current_crontab /tmp/new_crontab

# Ajouter les nouvelles tâches
echo "" >> /tmp/new_crontab
echo "# Rapports quotidiens MCP - Générés automatiquement" >> /tmp/new_crontab
echo "" >> /tmp/new_crontab

# Rapport du nœud Daznode à 7h00
echo "# Rapport quotidien nœud Daznode - 7h00 tous les jours" >> /tmp/new_crontab
echo "0 7 * * * cd $PROJECT_ROOT && python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1" >> /tmp/new_crontab
echo "" >> /tmp/new_crontab

# Rapport de santé de l'application à 7h05
echo "# Rapport quotidien santé application - 7h05 tous les jours" >> /tmp/new_crontab
echo "5 7 * * * cd $PROJECT_ROOT && python3 scripts/daily_app_health_report.py >> logs/app_health_report.log 2>&1" >> /tmp/new_crontab
echo "" >> /tmp/new_crontab

# Nettoyage des anciens logs - Dimanche 3h00
echo "# Nettoyage des anciens logs de rapports - Dimanche 3h00" >> /tmp/new_crontab
echo "0 3 * * 0 find $LOG_DIR -name '*_report.log' -mtime +30 -delete 2>/dev/null || true" >> /tmp/new_crontab

# Installer le nouveau crontab
crontab /tmp/new_crontab

# Nettoyer
rm -f /tmp/current_crontab /tmp/new_crontab

echo "✅ Configuration terminée!"
echo ""
echo "📊 Rapports quotidiens configurés:"
echo "   🏦 Rapport Daznode (nœud Lightning) : 7h00 tous les jours"
echo "   🏥 Rapport santé application (MCP)  : 7h05 tous les jours"
echo ""
echo "📝 Logs disponibles dans:"
echo "   • $LOG_DIR/daznode_report.log"
echo "   • $LOG_DIR/app_health_report.log"
echo ""
echo "🔍 Pour vérifier l'installation:"
echo "   crontab -l | grep -A5 -B5 'Rapports quotidiens MCP'"
echo ""
echo "🧪 Pour tester les rapports manuellement:"
echo "   cd $PROJECT_ROOT"
echo "   python3 scripts/test_daznode_report.py"
echo "   python3 scripts/test_app_health_report.py"
echo ""
echo "⚠️  Assurez-vous que les variables d'environnement suivantes sont définies:"
echo "   - TELEGRAM_BOT_TOKEN (obligatoire)"
echo "   - TELEGRAM_CHAT_ID (obligatoire)"
echo "   - FEUSTEY_NODE_ID (optionnel, valeur par défaut fournie)"
echo "   - LNBITS_URL (optionnel, par défaut: http://127.0.0.1:5000)"
echo "   - LNBITS_API_KEY (recommandé)"
echo "   - API_BASE_URL (optionnel, par défaut: http://localhost:8000)"
echo ""
echo "📱 Vous recevrez désormais chaque jour:"
echo "   🌅 7h00 - Rapport complet du nœud Lightning avec KPI et recommandations"
echo "   🌅 7h05 - Rapport de santé de l'application avec métriques système et endpoints"