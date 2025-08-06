#!/bin/bash

# 🚀 Script de Déploiement Automatique - Rapports Quotidiens MCP
# À exécuter sur le serveur de production après avoir copié les fichiers

set -e

echo "🚀 DÉPLOIEMENT DES RAPPORTS QUOTIDIENS MCP"
echo "=========================================="

# Configuration
PROJECT_ROOT="/home/feustey/MCP-1"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
LOGS_DIR="$PROJECT_ROOT/logs"

echo "📁 Vérification des répertoires..."
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$LOGS_DIR"

echo "🔐 Configuration des permissions..."
chmod +x daily_*.py
chmod +x test_*.py
chmod +x demo_*.py
chmod +x install_*.sh

echo "📋 Vérification des variables d'environnement..."
if [ -f "$PROJECT_ROOT/.env.production" ]; then
    echo "✅ Fichier .env.production trouvé"
    
    if grep -q "TELEGRAM_BOT_TOKEN.*YOUR_BOT_TOKEN" "$PROJECT_ROOT/.env.production" 2>/dev/null; then
        echo "⚠️  ATTENTION: Configurez TELEGRAM_BOT_TOKEN dans .env.production"
        echo "   Remplacez YOUR_BOT_TOKEN par votre token Telegram"
    fi
    
    if grep -q "TELEGRAM_CHAT_ID.*YOUR_CHAT_ID" "$PROJECT_ROOT/.env.production" 2>/dev/null; then
        echo "⚠️  ATTENTION: Configurez TELEGRAM_CHAT_ID dans .env.production"
        echo "   Remplacez YOUR_CHAT_ID par votre chat ID Telegram"
    fi
else
    echo "❌ Fichier .env.production non trouvé"
    echo "   Créez le fichier avec les variables Telegram"
fi

echo ""
echo "🧪 Test des rapports (sans envoi Telegram)..."
echo "----------------------------------------------"

# Test du système
cd "$PROJECT_ROOT"
echo "🏥 Test du rapport de santé..."
timeout 30 python3 scripts/demo_rapports_telegram.py || echo "⚠️  Test avec limitations"

echo ""
echo "📅 Installation des tâches cron..."
echo "----------------------------------"

# Sauvegarder le crontab actuel
crontab -l > /tmp/current_crontab 2>/dev/null || echo "# Nouveau crontab MCP" > /tmp/current_crontab

# Supprimer les anciennes tâches MCP
grep -v "daily_daznode_report.py\|daily_app_health_report.py\|# Rapports quotidiens MCP" /tmp/current_crontab > /tmp/new_crontab || cp /tmp/current_crontab /tmp/new_crontab

# Ajouter les nouvelles tâches
echo "" >> /tmp/new_crontab
echo "# Rapports quotidiens MCP - Générés automatiquement" >> /tmp/new_crontab
echo "" >> /tmp/new_crontab
echo "# Rapport quotidien nœud Daznode - 7h00 tous les jours" >> /tmp/new_crontab
echo "0 7 * * * cd $PROJECT_ROOT && python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1" >> /tmp/new_crontab
echo "" >> /tmp/new_crontab
echo "# Rapport quotidien santé application - 7h05 tous les jours" >> /tmp/new_crontab
echo "5 7 * * * cd $PROJECT_ROOT && python3 scripts/daily_app_health_report.py >> logs/app_health_report.log 2>&1" >> /tmp/new_crontab

# Installer le nouveau crontab
crontab /tmp/new_crontab
rm -f /tmp/current_crontab /tmp/new_crontab

echo "✅ Tâches cron installées!"

echo ""
echo "🔍 Vérification de l'installation..."
echo "------------------------------------"
crontab -l | grep -A3 -B1 "Rapports quotidiens MCP" || echo "❌ Problème avec les tâches cron"

echo ""
echo "🎯 DÉPLOIEMENT TERMINÉ!"
echo "======================="
echo ""
echo "📊 Rapports configurés:"
echo "   🏦 Rapport Daznode (nœud Lightning) : 7h00 tous les jours"
echo "   🏥 Rapport santé application (MCP)  : 7h05 tous les jours"
echo ""
echo "📝 Logs disponibles dans:"
echo "   • $LOGS_DIR/daznode_report.log"
echo "   • $LOGS_DIR/app_health_report.log"
echo ""
echo "🧪 Pour tester immédiatement:"
echo "   cd $PROJECT_ROOT"
echo "   python3 scripts/test_daznode_report.py"
echo "   python3 scripts/test_app_health_report.py"
echo ""
echo "📱 Assurez-vous que les variables Telegram sont configurées:"
echo "   TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID dans .env.production"
echo ""
echo "🎉 Vous recevrez les rapports chaque matin à 7h00 et 7h05 !"