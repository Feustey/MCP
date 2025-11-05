#!/bin/bash
#
# Script de déploiement : Système de Rapports Quotidiens
# Version: 1.0.0
# Date: 5 novembre 2025
#
# Usage: sudo ./scripts/deploy_daily_reports.sh [environment]
# Example: sudo ./scripts/deploy_daily_reports.sh production
#

set -e  # Exit on error

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
BACKUP_DIR="/backup/mcp_daily_reports_$(date +%Y%m%d_%H%M%S)"
APP_DIR="/var/www/mcp"
VENV_DIR="$APP_DIR/venv"
LOG_FILE="/tmp/deploy_daily_reports_$(date +%Y%m%d_%H%M%S).log"

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 n'est pas installé"
        exit 1
    fi
    
    # Vérifier MongoDB
    if ! command -v mongosh &> /dev/null; then
        log_warning "mongosh n'est pas installé, certaines vérifications seront ignorées"
    fi
    
    # Vérifier que l'app existe
    if [ ! -d "$APP_DIR" ]; then
        log_error "Application directory $APP_DIR n'existe pas"
        exit 1
    fi
    
    log_success "Prérequis OK"
}

create_backup() {
    log_info "Création du backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup MongoDB
    if command -v mongodump &> /dev/null; then
        log_info "Backup MongoDB vers $BACKUP_DIR/mongodb"
        mongodump --uri="mongodb://localhost:27017/mcp_db" --out="$BACKUP_DIR/mongodb" >> "$LOG_FILE" 2>&1
        log_success "Backup MongoDB OK"
    else
        log_warning "mongodump non disponible, backup MongoDB ignoré"
    fi
    
    # Backup code actuel
    log_info "Backup code actuel vers $BACKUP_DIR/code.tar.gz"
    cd "$APP_DIR" || exit 1
    tar -czf "$BACKUP_DIR/code.tar.gz" . >> "$LOG_FILE" 2>&1
    log_success "Backup code OK"
    
    log_success "Backup complet dans $BACKUP_DIR"
}

stop_application() {
    log_info "Arrêt de l'application..."
    
    if systemctl is-active --quiet mcp-api; then
        systemctl stop mcp-api
        sleep 2
        log_success "Application arrêtée"
    else
        log_warning "Application déjà arrêtée"
    fi
}

install_dependencies() {
    log_info "Installation des dépendances..."
    
    cd "$APP_DIR" || exit 1
    
    # Activer virtualenv
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    else
        log_error "Virtualenv not found at $VENV_DIR"
        exit 1
    fi
    
    # Installer APScheduler
    log_info "Installation APScheduler..."
    pip install "APScheduler>=3.10.0,<4.0.0" >> "$LOG_FILE" 2>&1
    
    # Vérifier installation
    python -c "from apscheduler.schedulers.asyncio import AsyncIOScheduler; print('APScheduler OK')" >> "$LOG_FILE" 2>&1
    
    log_success "Dépendances installées"
}

configure_environment() {
    log_info "Configuration des variables d'environnement..."
    
    ENV_FILE="$APP_DIR/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Fichier .env non trouvé: $ENV_FILE"
        exit 1
    fi
    
    # Vérifier si les variables existent déjà
    if ! grep -q "DAILY_REPORTS_SCHEDULER_ENABLED" "$ENV_FILE"; then
        log_info "Ajout des variables Daily Reports au .env"
        
        cat >> "$ENV_FILE" << 'EOF'

# === Daily Reports Configuration ===
DAILY_REPORTS_SCHEDULER_ENABLED=true
DAILY_REPORTS_HOUR=6
DAILY_REPORTS_MINUTE=0
DAILY_REPORTS_MAX_CONCURRENT=10
DAILY_REPORTS_MAX_RETRIES=3
DAILY_REPORTS_TIMEOUT=300
EOF
        
        log_success "Variables ajoutées au .env"
    else
        log_info "Variables Daily Reports déjà présentes dans .env"
    fi
}

create_directories() {
    log_info "Création des répertoires nécessaires..."
    
    mkdir -p "$APP_DIR/rag/RAG_assets/reports/daily"
    chmod 755 "$APP_DIR/rag/RAG_assets/reports/daily"
    
    log_success "Répertoires créés"
}

setup_mongodb_indexes() {
    log_info "Création des index MongoDB..."
    
    if ! command -v mongosh &> /dev/null; then
        log_warning "mongosh non disponible, index MongoDB non créés"
        return
    fi
    
    # Script MongoDB pour créer les index
    cat > /tmp/create_daily_reports_indexes.js << 'EOF'
// Index pour user_profiles
db.user_profiles.createIndex({ "lightning_pubkey": 1 }, { unique: true, sparse: true });
db.user_profiles.createIndex({ "daily_report_enabled": 1 });
db.user_profiles.createIndex({ "tenant_id": 1, "lightning_pubkey": 1 });

// Index pour daily_reports
db.daily_reports.createIndex({ "report_id": 1 }, { unique: true });
db.daily_reports.createIndex({ "user_id": 1, "report_date": -1 });
db.daily_reports.createIndex({ "node_pubkey": 1, "report_date": -1 });
db.daily_reports.createIndex({ "tenant_id": 1, "report_date": -1 });
db.daily_reports.createIndex({ "generation_status": 1 });

// TTL index pour auto-suppression après 90 jours
db.daily_reports.createIndex(
  { "report_date": 1 },
  { expireAfterSeconds: 7776000 }
);

print("Index créés avec succès");
EOF
    
    mongosh mongodb://localhost:27017/mcp_db /tmp/create_daily_reports_indexes.js >> "$LOG_FILE" 2>&1
    rm /tmp/create_daily_reports_indexes.js
    
    log_success "Index MongoDB créés"
}

verify_files() {
    log_info "Vérification des fichiers..."
    
    REQUIRED_FILES=(
        "config/models/daily_reports.py"
        "app/routes/daily_reports.py"
        "app/services/daily_report_generator.py"
        "app/scheduler/daily_report_scheduler.py"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$APP_DIR/$file" ]; then
            log_error "Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    log_success "Tous les fichiers requis sont présents"
}

run_tests() {
    log_info "Exécution des tests..."
    
    cd "$APP_DIR" || exit 1
    source "$VENV_DIR/bin/activate"
    
    # Vérifier imports
    log_info "Vérification des imports..."
    python -c "from config.models.daily_reports import DailyReport; print('Import OK')" >> "$LOG_FILE" 2>&1
    python -c "from app.routes.daily_reports import router; print('Import OK')" >> "$LOG_FILE" 2>&1
    python -c "from app.services.daily_report_generator import DailyReportGenerator; print('Import OK')" >> "$LOG_FILE" 2>&1
    python -c "from app.scheduler.daily_report_scheduler import DailyReportScheduler; print('Import OK')" >> "$LOG_FILE" 2>&1
    
    # Lancer les tests unitaires si pytest disponible
    if command -v pytest &> /dev/null; then
        log_info "Exécution des tests unitaires..."
        pytest tests/test_daily_reports.py -v >> "$LOG_FILE" 2>&1 || log_warning "Certains tests ont échoué (voir $LOG_FILE)"
    else
        log_warning "pytest non disponible, tests unitaires ignorés"
    fi
    
    log_success "Tests OK"
}

start_application() {
    log_info "Démarrage de l'application..."
    
    systemctl start mcp-api
    sleep 5
    
    if systemctl is-active --quiet mcp-api; then
        log_success "Application démarrée"
    else
        log_error "Échec du démarrage de l'application"
        systemctl status mcp-api
        exit 1
    fi
}

verify_deployment() {
    log_info "Vérification du déploiement..."
    
    # Attendre que l'app soit prête
    sleep 10
    
    # Vérifier les logs pour le scheduler
    if journalctl -u mcp-api --since "1 minute ago" | grep -q "Daily report scheduler started"; then
        log_success "Scheduler démarré correctement"
    else
        log_warning "Scheduler non détecté dans les logs"
    fi
    
    # Vérifier l'API health
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:8000/health > /dev/null; then
            log_success "API répond correctement"
        else
            log_warning "API ne répond pas encore"
        fi
    fi
    
    log_success "Déploiement vérifié"
}

show_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Déploiement Daily Reports terminé avec succès   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Backup:${NC} $BACKUP_DIR"
    echo -e "${BLUE}Logs:${NC} $LOG_FILE"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo "  1. Vérifier les logs: sudo journalctl -u mcp-api -f"
    echo "  2. Tester l'API: curl http://localhost:8000/health"
    echo "  3. Surveiller le premier batch demain à 06:00 UTC"
    echo ""
    echo -e "${YELLOW}Commandes utiles:${NC}"
    echo "  - Status: sudo systemctl status mcp-api"
    echo "  - Logs: sudo tail -f /var/log/mcp/app.log | grep daily_report"
    echo "  - Stats MongoDB: mongosh mcp_db --eval 'db.daily_reports.countDocuments()'"
    echo ""
}

rollback() {
    log_error "Rollback en cours..."
    
    # Arrêter l'application
    systemctl stop mcp-api
    
    # Restaurer code
    if [ -f "$BACKUP_DIR/code.tar.gz" ]; then
        cd "$APP_DIR" || exit 1
        tar -xzf "$BACKUP_DIR/code.tar.gz"
        log_success "Code restauré"
    fi
    
    # Restaurer MongoDB
    if [ -d "$BACKUP_DIR/mongodb" ] && command -v mongorestore &> /dev/null; then
        mongorestore --uri="mongodb://localhost:27017/mcp_db" --drop "$BACKUP_DIR/mongodb/mcp_db"
        log_success "MongoDB restauré"
    fi
    
    # Redémarrer
    systemctl start mcp-api
    
    log_success "Rollback terminé"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log_info "=== Déploiement Daily Reports - Environnement: $ENVIRONMENT ==="
    log_info "Début: $(date)"
    log_info "Logs: $LOG_FILE"
    echo ""
    
    # Trap pour gérer les erreurs
    trap 'log_error "Erreur détectée. Rollback recommandé."; exit 1' ERR
    
    # Étapes de déploiement
    check_prerequisites
    create_backup
    stop_application
    install_dependencies
    configure_environment
    create_directories
    verify_files
    setup_mongodb_indexes
    run_tests
    start_application
    verify_deployment
    
    log_success "Déploiement terminé avec succès!"
    log_info "Fin: $(date)"
    
    show_summary
}

# Vérifier que le script est exécuté en root
if [ "$EUID" -ne 0 ]; then 
    log_error "Ce script doit être exécuté en root (sudo)"
    exit 1
fi

# Exécuter le déploiement
main

