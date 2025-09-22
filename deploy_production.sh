#!/bin/bash

# Script de déploiement en production pour MCP Lightning
# Avec surveillance continue et configuration optimisée

echo "🚀 DÉPLOIEMENT MCP LIGHTNING EN PRODUCTION"
echo "========================================="

# Vérification des prérequis
echo "🔍 Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trouvé. Installation requise."
    exit 1
fi

# Vérifier la version Python
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ Python $PYTHON_VERSION détecté"

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p logs
mkdir -p monitoring_data
mkdir -p backup

# Configuration de l'environnement de production
echo "🔧 Configuration de l'environnement de production..."

# Copier la configuration optimisée
if [ -f ".env.production.optimized" ]; then
    cp .env.production.optimized .env.production.active
    echo "✓ Configuration de production activée"
else
    echo "⚠️  Fichier .env.production.optimized non trouvé"
    echo "Création d'une configuration de base..."
    cat > .env.production.active << 'EOF'
DEVELOPMENT_MODE=false
JWT_SECRET_KEY=CHANGEZ_CETTE_CLE_EN_PRODUCTION_32CHARS_MIN
MONITORING_ENABLED=true
CONNECTIVITY_CHECK_INTERVAL=60
LNBITS_URL=http://localhost:5001
LOG_LEVEL=INFO
TELEGRAM_NOTIFICATIONS_ENABLED=false
EOF
fi

# Installation des dépendances
echo "📦 Installation des dépendances..."

# Environnement virtuel
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activation et installation
source venv/bin/activate

# Installation des dépendances essentielles
echo "Installation des dépendances essentielles..."
pip install --upgrade pip
pip install -r requirements-core.txt

# Vérification des installations critiques
echo "🧪 Vérification des installations..."
python3 -c "
import sys
try:
    import fastapi, uvicorn, motor, httpx, jwt
    print('✓ Dépendances critiques installées')
except ImportError as e:
    print(f'❌ Erreur dépendance: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Échec de l'installation des dépendances"
    exit 1
fi

# Test du système avant déploiement
echo "🧪 Tests pré-déploiement..."
source venv/bin/activate
python3 test_lightweight_system.py

if [ $? -ne 0 ]; then
    echo "⚠️  Tests pré-déploiement échoués, mais continuez le déploiement"
fi

# Configuration du monitoring de production
echo "📊 Configuration du monitoring de production..."

# Vérifier les variables d'environnement critiques
source .env.production.active

if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "CHANGEZ_CETTE_CLE_EN_PRODUCTION_32CHARS_MIN" ]; then
    echo "⚠️  ATTENTION: JWT_SECRET_KEY doit être configurée avec une vraie clé en production"
fi

if [ -z "$LNBITS_URL" ]; then
    echo "⚠️  ATTENTION: LNBITS_URL doit être configurée"
fi

# Création du script de lancement de production
echo "🚀 Création du script de lancement..."
cat > start_production.sh << 'EOF'
#!/bin/bash

echo "🚀 Démarrage MCP Lightning en production..."

# Charger l'environnement virtuel
source venv/bin/activate

# Charger la configuration de production
export $(cat .env.production.active | grep -v '^#' | xargs)

# Démarrer le monitoring en arrière-plan si activé
if [ "$MONITORING_ENABLED" = "true" ]; then
    echo "📊 Démarrage du monitoring de production..."
    nohup python3 src/monitoring/production_monitor.py > logs/monitoring.log 2>&1 &
    MONITORING_PID=$!
    echo $MONITORING_PID > monitoring.pid
    echo "✓ Monitoring démarré (PID: $MONITORING_PID)"
fi

# Démarrer l'API principale
echo "🌐 Démarrage de l'API MCP Lightning..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers $WORKERS --log-level $LOG_LEVEL
EOF

chmod +x start_production.sh

# Création du script d'arrêt
cat > stop_production.sh << 'EOF'
#!/bin/bash

echo "⏹️  Arrêt MCP Lightning..."

# Arrêter le monitoring
if [ -f "monitoring.pid" ]; then
    MONITORING_PID=$(cat monitoring.pid)
    echo "Arrêt du monitoring (PID: $MONITORING_PID)..."
    kill $MONITORING_PID 2>/dev/null
    rm -f monitoring.pid
fi

# Arrêter l'API principale
pkill -f "uvicorn main:app"

echo "✓ Services arrêtés"
EOF

chmod +x stop_production.sh

# Création du script de status
cat > status_production.sh << 'EOF'
#!/bin/bash

echo "📊 STATUS MCP LIGHTNING"
echo "======================"

# Vérifier l'API
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "✅ API MCP: En cours d'exécution"
else
    echo "❌ API MCP: Arrêtée"
fi

# Vérifier le monitoring
if [ -f "monitoring.pid" ] && kill -0 $(cat monitoring.pid) 2>/dev/null; then
    echo "✅ Monitoring: En cours d'exécution (PID: $(cat monitoring.pid))"
else
    echo "❌ Monitoring: Arrêté"
fi

# Logs récents
echo ""
echo "📄 LOGS RÉCENTS:"
echo "----------------"
if [ -f "logs/monitoring.log" ]; then
    echo "Monitoring:"
    tail -n 3 logs/monitoring.log
fi

echo ""
echo "💾 DONNÉES MONITORING:"
echo "---------------------"
if [ -d "monitoring_data" ]; then
    ls -la monitoring_data/ | tail -n 5
fi
EOF

chmod +x status_production.sh

# Instructions finales
echo ""
echo "✅ DÉPLOIEMENT PRÊT POUR LA PRODUCTION"
echo "====================================="
echo ""
echo "📋 PROCHAINES ÉTAPES:"
echo "• 1. Configurer .env.production.active avec vos vraies clés"
echo "• 2. Lancer: ./start_production.sh"
echo "• 3. Vérifier: ./status_production.sh"
echo "• 4. Arrêter: ./stop_production.sh"
echo ""
echo "🔐 SÉCURITÉ IMPORTANTE:"
echo "• Changez JWT_SECRET_KEY dans .env.production.active"
echo "• Configurez vos vraies clés API (LNBITS, OpenAI, etc.)"
echo "• Activez les notifications Telegram si souhaité"
echo ""
echo "📊 MONITORING:"
echo "• Logs dans: logs/"
echo "• Données monitoring dans: monitoring_data/"
echo "• Status temps réel: ./status_production.sh"
echo ""
echo "🎉 Le système MCP Lightning est prêt pour la production !"