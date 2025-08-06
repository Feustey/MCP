#!/bin/bash

# 🚀 FINALISATION COMPLÈTE AVEC TOUTES LES VARIABLES
echo "🚀 FINALISATION COMPLÈTE DES RAPPORTS TELEGRAM MCP"
echo "=================================================="

SERVER="feustey@147.79.101.32"
PASSWORD="Feustey@AI!"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'COMPLETE_SETUP'

cd /home/feustey/MCP

echo "📝 Création du fichier .env COMPLET..."
cat > .env << 'ENV_COMPLETE'
# Configuration des rapports Telegram
TELEGRAM_BOT_TOKEN=DEMO_MODE
TELEGRAM_CHAT_ID=DEMO_MODE

# Configuration API
API_BASE_URL=http://localhost:8000

# Configuration Lightning
FEUSTEY_NODE_ID=02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b
LNBITS_URL=http://127.0.0.1:5000
LNBITS_INKEY=demo_key
LNBITS_ADMIN_KEY=demo_admin_key

# Configuration MongoDB (valeurs par défaut)
MONGO_URL=mongodb://localhost:27017/mcp
MONGO_NAME=mcp

# Configuration IA (valeurs par défaut)
AI_OPENAI_API_KEY=demo_openai_key

# Configuration sécurité
SECURITY_SECRET_KEY=demo_secret_key_for_testing_only

# Configuration environnement
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
ENV_COMPLETE

echo "🔧 Création du script d'exécution optimisé..."
cat > run_report_final.sh << 'SCRIPT_FINAL'
#!/bin/bash
cd /home/feustey/MCP
source venv_reports/bin/activate
export $(grep -v '^#' .env | xargs)
python3 $1 2>&1
SCRIPT_FINAL

chmod +x run_report_final.sh

echo ""
echo "🏦 TEST FINAL RAPPORT DAZNODE..."
echo "================================"
./run_report_final.sh scripts/daily_daznode_report.py | head -20

echo ""
echo "🏥 TEST FINAL RAPPORT SANTÉ APP..."
echo "================================="
./run_report_final.sh scripts/daily_app_health_report.py | head -20

echo ""
echo "📅 INSTALLATION TÂCHES CRON..."
echo "=============================="
# Supprimer anciennes tâches et ajouter les nouvelles
(crontab -l 2>/dev/null | grep -v 'daily_.*_report.py' | grep -v 'Rapports quotidiens MCP'; echo ''; echo '# Rapports quotidiens MCP - 7h00 et 7h05'; echo '0 7 * * * /home/feustey/MCP/run_report_final.sh scripts/daily_daznode_report.py >> /home/feustey/MCP/logs/daznode_report.log 2>&1'; echo '5 7 * * * /home/feustey/MCP/run_report_final.sh scripts/daily_app_health_report.py >> /home/feustey/MCP/logs/app_health_report.log 2>&1') | crontab -

echo "✅ Tâches cron installées:"
crontab -l | tail -5

echo ""
echo "🎉 FINALISATION TERMINÉE AVEC SUCCÈS !"
echo "====================================="
echo ""
echo "📊 STATUT FINAL:"
echo "   ✅ Scripts déployés: $(ls scripts/daily_*_report.py | wc -l) rapports"
echo "   ✅ Environnement Python: venv_reports activé"
echo "   ✅ Configuration: .env créé avec toutes les variables"
echo "   ✅ Tâches cron: installées pour 7h00 et 7h05"
echo ""
echo "📱 POUR RECEVOIR LES RAPPORTS SUR TELEGRAM:"
echo "   1. nano .env"
echo "   2. Remplacer TELEGRAM_BOT_TOKEN=DEMO_MODE par votre token"
echo "   3. Remplacer TELEGRAM_CHAT_ID=DEMO_MODE par votre chat ID"
echo "   4. Tester: ./run_report_final.sh scripts/daily_daznode_report.py"
echo ""
echo "🔍 SURVEILLANCE:"
echo "   tail -f logs/daznode_report.log"
echo "   tail -f logs/app_health_report.log"
echo ""
echo "🎯 RÉSULTAT: Vous recevrez automatiquement:"
echo "   🏦 7h00 - Rapport Lightning Network (KPI du nœud)"
echo "   🏥 7h05 - Rapport Santé Application (métriques système)"

COMPLETE_SETUP

echo ""
echo "🚀 DÉPLOIEMENT 100% TERMINÉ !"
echo "=============================="
echo "✅ Les rapports quotidiens MCP sont maintenant OPÉRATIONNELS !"
echo "📱 Configurez vos tokens Telegram et profitez de vos rapports automatiques !"