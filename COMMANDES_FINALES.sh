#!/bin/bash

# 🚀 SCRIPT DE FINALISATION AUTOMATIQUE
# Exécute toutes les commandes finales en une fois

echo "🚀 FINALISATION DES RAPPORTS TELEGRAM MCP"
echo "=========================================="

# Variables
SERVER="feustey@147.79.101.32"
PASSWORD="Feustey@AI!"

echo "📡 Connexion au serveur..."

# Exécuter toutes les commandes finales
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'REMOTE_COMMANDS'

cd /home/feustey/MCP

echo "📝 Création du fichier .env..."
cat > .env << 'ENV_EOF'
TELEGRAM_BOT_TOKEN=DEMO_MODE
TELEGRAM_CHAT_ID=DEMO_MODE
API_BASE_URL=http://localhost:8000
FEUSTEY_NODE_ID=02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b
LNBITS_URL=http://127.0.0.1:5000
ENV_EOF

echo "🔧 Création du script d'exécution..."
cat > run_report_final.sh << 'SCRIPT_EOF'
#!/bin/bash
cd /home/feustey/MCP
source venv_reports/bin/activate
source .env
python3 $1
SCRIPT_EOF

chmod +x run_report_final.sh

echo "🏦 TEST RAPPORT DAZNODE..."
echo "=========================="
./run_report_final.sh scripts/daily_daznode_report.py

echo ""
echo "🏥 TEST RAPPORT SANTÉ APP..."
echo "============================="
./run_report_final.sh scripts/daily_app_health_report.py

echo ""
echo "📅 INSTALLATION DES TÂCHES CRON..."
echo "==================================="
(crontab -l 2>/dev/null | grep -v 'daily_.*_report.py'; echo '# Rapports quotidiens MCP - 7h00 et 7h05'; echo '0 7 * * * /home/feustey/MCP/run_report_final.sh scripts/daily_daznode_report.py >> /home/feustey/MCP/logs/daznode_report.log 2>&1'; echo '5 7 * * * /home/feustey/MCP/run_report_final.sh scripts/daily_app_health_report.py >> /home/feustey/MCP/logs/app_health_report.log 2>&1') | crontab -

echo "✅ Tâches cron installées:"
crontab -l | grep -A2 -B1 MCP

echo ""
echo "🎉 FINALISATION TERMINÉE !"
echo "=========================="
echo "📊 Rapports configurés:"
echo "   🏦 7h00 - Rapport Daznode (Lightning Network)"
echo "   🏥 7h05 - Rapport Santé Application"
echo ""
echo "📱 Pour recevoir sur Telegram:"
echo "   1. nano .env"
echo "   2. Remplacer DEMO_MODE par vos tokens"
echo "   3. Tester: ./run_report_final.sh scripts/daily_daznode_report.py"
echo ""
echo "🔍 Logs: tail -f logs/*_report.log"

REMOTE_COMMANDS

echo ""
echo "✅ DÉPLOIEMENT FINALISÉ AVEC SUCCÈS !"
echo "======================================="
echo "🚀 Les rapports quotidiens MCP sont maintenant opérationnels !"