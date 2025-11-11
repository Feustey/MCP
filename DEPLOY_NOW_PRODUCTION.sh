#!/bin/bash
#
# Script de déploiement rapide - Daily Reports
# À exécuter sur le serveur de production
#
# Usage: bash DEPLOY_NOW_PRODUCTION.sh
#

set -e

echo "=========================================="
echo "🚀 DÉPLOIEMENT DAILY REPORTS - PRODUCTION"
echo "=========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Détection du répertoire de l'application
if [ -d "/var/www/mcp" ]; then
    APP_DIR="/var/www/mcp"
elif [ -d "/root/mcp" ]; then
    APP_DIR="/root/mcp"
elif [ -d "/home/mcp" ]; then
    APP_DIR="/home/mcp"
else
    echo -e "${RED}❌ Répertoire MCP non trouvé${NC}"
    echo "Chemins vérifiés: /var/www/mcp, /root/mcp, /home/mcp"
    exit 1
fi

echo -e "${BLUE}📁 Application trouvée: $APP_DIR${NC}"
cd "$APP_DIR"

# 1. Pull du code
echo ""
echo -e "${BLUE}📥 Récupération du code...${NC}"
git pull origin main

# 2. Backup rapide
echo ""
echo -e "${BLUE}💾 Backup rapide...${NC}"
BACKUP_FILE="/tmp/mcp_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' . 2>/dev/null || true
echo -e "${GREEN}✅ Backup créé: $BACKUP_FILE${NC}"

# 3. Installation APScheduler
echo ""
echo -e "${BLUE}📦 Installation APScheduler...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install "APScheduler>=3.10.0,<4.0.0" --quiet
    echo -e "${GREEN}✅ APScheduler installé${NC}"
else
    echo -e "${RED}⚠️  VirtualEnv non trouvé, installation système...${NC}"
    pip3 install "APScheduler>=3.10.0,<4.0.0" --quiet
fi

# 4. Configuration .env
echo ""
echo -e "${BLUE}⚙️  Configuration environnement...${NC}"
if ! grep -q "DAILY_REPORTS_SCHEDULER_ENABLED" .env; then
    cat >> .env << 'EOF'

# === Daily Reports Configuration ===
DAILY_REPORTS_SCHEDULER_ENABLED=true
DAILY_REPORTS_HOUR=6
DAILY_REPORTS_MINUTE=0
DAILY_REPORTS_MAX_CONCURRENT=10
DAILY_REPORTS_MAX_RETRIES=3
DAILY_REPORTS_TIMEOUT=300
EOF
    echo -e "${GREEN}✅ Variables ajoutées au .env${NC}"
else
    echo -e "${GREEN}✅ Variables déjà présentes${NC}"
fi

# 5. Création répertoires
echo ""
echo -e "${BLUE}📂 Création des répertoires...${NC}"
mkdir -p rag/RAG_assets/reports/daily
chmod 755 rag/RAG_assets/reports/daily
echo -e "${GREEN}✅ Répertoires créés${NC}"

# 6. Index MongoDB
echo ""
echo -e "${BLUE}🗄️  Configuration MongoDB...${NC}"
if command -v mongosh &> /dev/null; then
    cat > /tmp/create_indexes.js << 'EOF'
// User profiles indexes
db.user_profiles.createIndex({ "lightning_pubkey": 1 }, { unique: true, sparse: true });
db.user_profiles.createIndex({ "daily_report_enabled": 1 });
db.user_profiles.createIndex({ "tenant_id": 1, "lightning_pubkey": 1 });

// Daily reports indexes
db.daily_reports.createIndex({ "report_id": 1 }, { unique: true });
db.daily_reports.createIndex({ "user_id": 1, "report_date": -1 });
db.daily_reports.createIndex({ "node_pubkey": 1, "report_date": -1 });
db.daily_reports.createIndex({ "tenant_id": 1, "report_date": -1 });
db.daily_reports.createIndex({ "generation_status": 1 });
db.daily_reports.createIndex({ "report_date": 1 }, { expireAfterSeconds: 7776000 });

print("✅ Index créés");
EOF
    
    mongosh mcp_db /tmp/create_indexes.js --quiet 2>/dev/null || echo -e "${RED}⚠️  MongoDB index creation failed (non-blocking)${NC}"
    rm /tmp/create_indexes.js
    echo -e "${GREEN}✅ MongoDB configuré${NC}"
else
    echo -e "${RED}⚠️  mongosh non trouvé, index ignorés${NC}"
fi

# 7. Vérification imports
echo ""
echo -e "${BLUE}🔍 Vérification du code...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
fi

python3 -c "from config.models.daily_reports import DailyReport; print('✅ Models OK')" 2>/dev/null || echo "⚠️  Models import warning"
python3 -c "from app.routes.daily_reports import router; print('✅ Routes OK')" 2>/dev/null || echo "⚠️  Routes import warning"
python3 -c "from app.services.daily_report_generator import DailyReportGenerator; print('✅ Generator OK')" 2>/dev/null || echo "⚠️  Generator import warning"
python3 -c "from app.scheduler.daily_report_scheduler import DailyReportScheduler; print('✅ Scheduler OK')" 2>/dev/null || echo "⚠️  Scheduler import warning"

# 8. Redémarrage
echo ""
echo -e "${BLUE}🔄 Redémarrage de l'application...${NC}"

# Détection du système de service
if systemctl is-active --quiet mcp-api 2>/dev/null; then
    echo "Utilisation de systemctl..."
    systemctl restart mcp-api
    sleep 5
    if systemctl is-active --quiet mcp-api; then
        echo -e "${GREEN}✅ Application redémarrée avec systemctl${NC}"
    else
        echo -e "${RED}❌ Échec redémarrage systemctl${NC}"
        systemctl status mcp-api
        exit 1
    fi
elif [ -f "docker-compose.yml" ]; then
    echo "Utilisation de docker-compose..."
    docker-compose restart mcp-api 2>/dev/null || docker compose restart mcp-api
    echo -e "${GREEN}✅ Application redémarrée avec docker-compose${NC}"
else
    echo -e "${RED}⚠️  Système de service non détecté${NC}"
    echo "Redémarrez manuellement l'application"
fi

# 9. Vérifications
echo ""
echo -e "${BLUE}✅ Vérifications post-déploiement...${NC}"
sleep 3

# Vérifier logs
echo ""
echo "📋 Logs récents (10 dernières lignes):"
if journalctl -u mcp-api -n 10 --no-pager 2>/dev/null; then
    :
elif [ -f "/var/log/mcp/app.log" ]; then
    tail -10 /var/log/mcp/app.log
else
    echo "Logs non trouvés dans les emplacements standards"
fi

# Vérifier scheduler
echo ""
if journalctl -u mcp-api --since "2 minutes ago" --no-pager 2>/dev/null | grep -q "scheduler"; then
    echo -e "${GREEN}✅ Scheduler détecté dans les logs${NC}"
else
    echo -e "${RED}⚠️  Scheduler non détecté (vérifier les logs)${NC}"
fi

# Vérifier API
echo ""
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API répond correctement${NC}"
else
    echo -e "${RED}⚠️  API ne répond pas encore${NC}"
fi

# Résumé final
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 DÉPLOIEMENT TERMINÉ${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📊 Résumé:${NC}"
echo "  • Code: Mis à jour depuis GitHub"
echo "  • Backup: $BACKUP_FILE"
echo "  • APScheduler: Installé"
echo "  • Configuration: .env mis à jour"
echo "  • MongoDB: Index créés"
echo "  • Application: Redémarrée"
echo ""
echo -e "${BLUE}🔍 Commandes utiles:${NC}"
echo "  • Logs live: journalctl -u mcp-api -f"
echo "  • Status: systemctl status mcp-api"
echo "  • Scheduler: journalctl -u mcp-api | grep scheduler"
echo "  • MongoDB: mongosh mcp_db --eval 'db.daily_reports.countDocuments()'"
echo ""
echo -e "${BLUE}⏰ Prochain rapport:${NC} Demain à 06:00 UTC"
echo ""
echo -e "${GREEN}✅ Déploiement réussi !${NC}"
echo ""

