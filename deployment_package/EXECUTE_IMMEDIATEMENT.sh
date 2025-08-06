#!/bin/bash

# 🚀 SCRIPT D'EXÉCUTION IMMÉDIATE - TRANSFERT ET TEST DES ALERTES
# À exécuter dès que le serveur est accessible

echo "🚀 TRANSFERT ET DÉPLOIEMENT IMMÉDIAT DES ALERTES MCP"
echo "===================================================="

SERVER="feustey@147.79.101.32"
PASSWORD="Feustey@AI!"
LOCAL_PATH="deployment_package/*"
REMOTE_PATH="/home/feustey/MCP-1/scripts/"

echo "📡 Test de connectivité..."
if ! ping -c 1 147.79.101.32 > /dev/null 2>&1; then
    echo "❌ Serveur non accessible - Relancez ce script plus tard"
    exit 1
fi

echo "✅ Serveur accessible"

echo ""
echo "📦 ÉTAPE 1: TRANSFERT DES FICHIERS"
echo "=================================="

# Transférer tous les fichiers
echo "📁 Transfert des fichiers de déploiement..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no $LOCAL_PATH $SERVER:$REMOTE_PATH

if [ $? -eq 0 ]; then
    echo "✅ Fichiers transférés avec succès"
else
    echo "❌ Erreur lors du transfert"
    exit 1
fi

echo ""
echo "🔧 ÉTAPE 2: DÉPLOIEMENT SUR LE SERVEUR"
echo "======================================"

# Exécuter le déploiement
echo "🚀 Exécution du déploiement automatique..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'DEPLOY_EOF'
cd /home/feustey/MCP-1
echo "📍 Dans le répertoire: $(pwd)"

# Rendre exécutable et lancer le déploiement
chmod +x scripts/DEPLOY_NOW.sh
./scripts/DEPLOY_NOW.sh

echo ""
echo "📊 Vérification des tâches cron installées:"
crontab -l | grep -A3 -B1 "MCP" || echo "❌ Pas de tâches MCP trouvées"
DEPLOY_EOF

echo ""
echo "🐳 ÉTAPE 3: RELANCE DES SERVICES"
echo "================================"

echo "🔄 Relance des services Docker MCP..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'SERVICES_EOF'
cd /home/feustey/MCP-1

echo "📊 État actuel des conteneurs:"
docker ps -a | grep mcp || echo "Aucun conteneur MCP trouvé"

echo ""
echo "🔄 Relance des services..."

# Arrêter les services existants
echo "⏹️  Arrêt des services..."
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || echo "Services déjà arrêtés"

# Relancer les services
echo "🚀 Démarrage des services..."
docker-compose up -d 2>/dev/null || docker compose up -d 2>/dev/null || echo "❌ Erreur démarrage Docker"

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services (30s)..."
sleep 30

echo "📊 État final des conteneurs:"
docker ps | grep mcp || echo "❌ Aucun conteneur MCP en cours"

echo "🔍 Test de l'API:"
curl -s http://localhost:8000/health | head -50 || echo "❌ API non accessible"
SERVICES_EOF

echo ""
echo "📱 ÉTAPE 4: TEST DES ALERTES TELEGRAM"
echo "===================================="

echo "🧪 Lancement des tests des alertes..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'TEST_EOF'
cd /home/feustey/MCP-1

echo "📋 Vérification de la configuration Telegram..."

# Vérifier les variables Telegram dans .env.production
if [ -f .env.production ]; then
    if grep -q "TELEGRAM_BOT_TOKEN.*YOUR_BOT_TOKEN" .env.production 2>/dev/null; then
        echo "⚠️  TELEGRAM_BOT_TOKEN non configuré dans .env.production"
        echo "   Ajoutez votre token de @BotFather"
    else
        echo "✅ TELEGRAM_BOT_TOKEN configuré"
    fi
    
    if grep -q "TELEGRAM_CHAT_ID.*YOUR_CHAT_ID" .env.production 2>/dev/null; then
        echo "⚠️  TELEGRAM_CHAT_ID non configuré dans .env.production"
        echo "   Ajoutez votre ID de @userinfobot"
    else
        echo "✅ TELEGRAM_CHAT_ID configuré"
    fi
else
    echo "❌ Fichier .env.production non trouvé"
fi

echo ""
echo "🏦 TEST 1: RAPPORT DAZNODE (Lightning Network)"
echo "----------------------------------------------"
python3 scripts/daily_daznode_report.py

echo ""
echo "🏥 TEST 2: RAPPORT SANTÉ APPLICATION"
echo "------------------------------------"
python3 scripts/daily_app_health_report.py

echo ""
echo "📊 LOGS DES RAPPORTS:"
echo "--------------------"
echo "📝 Dernières lignes du log Daznode:"
tail -5 logs/daznode_report.log 2>/dev/null || echo "Pas de log Daznode encore"

echo ""
echo "📝 Dernières lignes du log Santé:"
tail -5 logs/app_health_report.log 2>/dev/null || echo "Pas de log Santé encore"
TEST_EOF

echo ""
echo "🎉 DÉPLOIEMENT ET TESTS TERMINÉS !"
echo "=================================="
echo ""
echo "📱 Vérifiez vos messages Telegram - vous devriez avoir reçu :"
echo "   🏦 Rapport quotidien Daznode avec KPI du nœud Lightning"
echo "   🏥 Rapport santé application avec métriques système"
echo ""
echo "⏰ Les rapports automatiques sont programmés :"
echo "   📅 7h00 - Rapport Daznode"
echo "   📅 7h05 - Rapport Santé Application"
echo ""
echo "🔍 Pour surveiller les logs en continu :"
echo "   ssh $SERVER 'tail -f /home/feustey/MCP-1/logs/*_report.log'"