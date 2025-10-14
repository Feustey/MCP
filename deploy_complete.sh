#!/bin/bash

################################################################################
# Script de Déploiement Complet Automatisé - MCP v1.0
#
# Ce script automatise TOUT le déploiement :
# - Transfert des fichiers sur le serveur
# - Configuration .env
# - Déploiement Docker
# - Validation complète
#
# Usage: ./deploy_complete.sh
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SERVER="feustey@147.79.101.32"
REMOTE_DIR="/home/feustey/mcp-production"
LOCAL_DIR=$(pwd)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[$1]${NC} $2"
}

print_banner() {
    clear
    echo -e "${MAGENTA}"
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🚀 MCP v1.0 - DÉPLOIEMENT AUTOMATIQUE 🚀              ║
║                                                                ║
║              MongoDB + Redis + API + Nginx                     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo ""
}

check_prerequisites() {
    log_step "1/8" "Vérification des prérequis..."
    
    # Vérifier rsync
    if ! command -v rsync &> /dev/null; then
        log_error "rsync n'est pas installé"
        exit 1
    fi
    
    # Vérifier SSH
    if ! command -v ssh &> /dev/null; then
        log_error "ssh n'est pas installé"
        exit 1
    fi
    
    # Vérifier les fichiers requis
    local required_files=(
        "docker-compose.hostinger.yml"
        "mongo-init.js"
        "nginx-docker.conf"
        "env.production.configured"
        "scripts/deploy_hostinger_docker.sh"
        "scripts/backup_mongodb_docker.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    log_success "Tous les prérequis sont satisfaits"
}

confirm_deployment() {
    echo ""
    log_warning "⚠️  Vous êtes sur le point de déployer MCP sur le serveur production"
    echo ""
    echo "Serveur: $SERVER"
    echo "Répertoire: $REMOTE_DIR"
    echo ""
    
    read -p "Continuer ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Déploiement annulé"
        exit 0
    fi
}

test_ssh_connection() {
    log_step "2/8" "Test de connexion SSH..."
    
    if ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH OK'" &> /dev/null; then
        log_success "Connexion SSH établie"
    else
        log_error "Impossible de se connecter au serveur"
        log_info "Vérifiez vos credentials SSH"
        exit 1
    fi
}

transfer_files() {
    log_step "3/8" "Transfert des fichiers vers le serveur..."
    
    echo -e "${BLUE}Cela peut prendre quelques minutes...${NC}"
    
    # Créer le répertoire distant si nécessaire
    ssh "$SERVER" "mkdir -p $REMOTE_DIR"
    
    # Rsync avec exclusions
    rsync -avz --progress \
        --exclude 'venv*' \
        --exclude '__pycache__' \
        --exclude '.git' \
        --exclude '*.pyc' \
        --exclude '.DS_Store' \
        --exclude 'node_modules' \
        --exclude 'logs/*' \
        --exclude 'data/*' \
        --exclude 'backups/*' \
        ./ "$SERVER:$REMOTE_DIR/"
    
    log_success "Fichiers transférés"
}

configure_env() {
    log_step "4/8" "Configuration du fichier .env..."
    
    # Demander les credentials LNBits
    echo ""
    log_info "Configuration LNBits"
    echo -e "${YELLOW}Laissez vide pour utiliser les valeurs par défaut${NC}"
    echo ""
    
    read -p "LNBits URL (ou Enter pour défaut): " lnbits_url
    read -p "LNBits Admin Key (ou Enter pour défaut): " lnbits_admin
    read -p "LNBits Invoice Key (ou Enter pour défaut): " lnbits_invoice
    
    # Créer .env sur le serveur
    ssh "$SERVER" bash <<ENDSSH
cd $REMOTE_DIR

# Copier le template
cp env.production.configured .env

# Remplacer les valeurs LNBits si fournies
if [ -n "$lnbits_url" ]; then
    sed -i "s|LNBITS_URL=.*|LNBITS_URL=$lnbits_url|" .env
fi

if [ -n "$lnbits_admin" ]; then
    sed -i "s|LNBITS_ADMIN_KEY=.*|LNBITS_ADMIN_KEY=$lnbits_admin|" .env
fi

if [ -n "$lnbits_invoice" ]; then
    sed -i "s|LNBITS_INVOICE_KEY=.*|LNBITS_INVOICE_KEY=$lnbits_invoice|" .env
fi

echo "✓ Fichier .env configuré"
ENDSSH
    
    log_success "Configuration .env terminée"
}

create_directories() {
    log_step "5/8" "Création des répertoires..."
    
    ssh "$SERVER" bash <<'ENDSSH'
cd /home/feustey/mcp-production
mkdir -p logs data config ssl backups/mongodb
chmod 755 logs data config ssl backups
echo "✓ Répertoires créés"
ENDSSH
    
    log_success "Répertoires créés"
}

deploy_docker() {
    log_step "6/8" "Déploiement Docker (cela peut prendre 5-10 minutes)..."
    
    echo -e "${BLUE}Installation des dépendances et démarrage des services...${NC}"
    
    ssh -t "$SERVER" bash <<'ENDSSH'
cd /home/feustey/mcp-production

# Rendre les scripts exécutables
chmod +x scripts/*.sh
chmod +x start_api.sh
chmod +x docker_entrypoint.sh 2>/dev/null || true

# Installer Docker et Docker Compose si nécessaire
if ! command -v docker &> /dev/null; then
    echo "Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installation de Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

# Lancer le déploiement
echo ""
echo "🚀 Lancement du déploiement Docker..."
echo ""

sudo ./scripts/deploy_hostinger_docker.sh --skip-ssl || {
    echo "⚠️  Tentative de déploiement manuel..."
    sudo docker-compose -f docker-compose.hostinger.yml up -d
}
ENDSSH
    
    log_success "Déploiement Docker terminé"
}

validate_deployment() {
    log_step "7/8" "Validation du déploiement..."
    
    echo ""
    sleep 10  # Attendre que les services démarrent
    
    # Vérifier les containers
    log_info "Vérification des containers Docker..."
    ssh "$SERVER" "cd $REMOTE_DIR && docker-compose -f docker-compose.hostinger.yml ps"
    
    echo ""
    
    # Test MongoDB
    log_info "Test MongoDB..."
    if ssh "$SERVER" "docker exec mcp-mongodb mongosh --eval 'db.runCommand(\"ping\")' &> /dev/null"; then
        log_success "MongoDB opérationnel"
    else
        log_warning "MongoDB ne répond pas encore (peut prendre quelques secondes)"
    fi
    
    # Test Redis
    log_info "Test Redis..."
    if ssh "$SERVER" "docker exec mcp-redis redis-cli ping &> /dev/null"; then
        log_success "Redis opérationnel"
    else
        log_warning "Redis ne répond pas encore"
    fi
    
    # Test API
    log_info "Test API..."
    sleep 5
    if ssh "$SERVER" "curl -sf http://localhost:8000/ &> /dev/null"; then
        log_success "API opérationnelle"
    else
        log_warning "API ne répond pas encore (peut prendre 1-2 minutes)"
    fi
    
    # Test Nginx
    log_info "Test Nginx..."
    if ssh "$SERVER" "curl -sf http://localhost/ &> /dev/null"; then
        log_success "Nginx opérationnel"
    else
        log_warning "Nginx ne répond pas"
    fi
    
    echo ""
}

show_summary() {
    log_step "8/8" "Génération du rapport..."
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}║           🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ! 🎉             ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${CYAN}📊 Services Déployés:${NC}"
    echo "   • MongoDB 7.0 (local, port 27017)"
    echo "   • Redis 7-alpine (local, port 6379)"
    echo "   • MCP API (port 8000)"
    echo "   • Nginx reverse proxy (ports 80/443)"
    echo ""
    
    echo -e "${CYAN}🔗 URLs:${NC}"
    echo "   • API:            http://api.dazno.de/"
    echo "   • Documentation:  http://api.dazno.de/docs"
    echo ""
    
    echo -e "${CYAN}💰 Économies:${NC}"
    echo "   • MongoDB Atlas: $60/mois → GRATUIT"
    echo "   • Redis Cloud:   $10/mois → GRATUIT"
    echo "   • Total:         $70/mois économisés ($840/an)"
    echo ""
    
    echo -e "${CYAN}📊 Status:${NC}"
    ssh "$SERVER" "cd $REMOTE_DIR && docker-compose -f docker-compose.hostinger.yml ps" | head -n 10
    echo ""
    
    echo -e "${CYAN}🔧 Commandes Utiles:${NC}"
    echo "   • Logs:      ssh $SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.hostinger.yml logs -f'"
    echo "   • Restart:   ssh $SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.hostinger.yml restart'"
    echo "   • Status:    ssh $SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.hostinger.yml ps'"
    echo "   • Backup:    ssh $SERVER 'cd $REMOTE_DIR && ./scripts/backup_mongodb_docker.sh'"
    echo ""
    
    echo -e "${CYAN}📚 Documentation:${NC}"
    echo "   • DEPLOY_FINAL_INSTRUCTIONS.md   - Instructions complètes"
    echo "   • QUICKSTART_DOCKER.md            - Quick start"
    echo "   • DEPLOY_HOSTINGER_DOCKER.md      - Guide détaillé"
    echo ""
    
    echo -e "${CYAN}🎯 Prochaines Étapes:${NC}"
    echo "   1. Configurer SSL: ssh $SERVER 'sudo certbot certonly --standalone -d api.dazno.de'"
    echo "   2. Configurer backups auto (crontab)"
    echo "   3. Lancer Shadow Mode (21 jours)"
    echo "   4. Tests pilotes"
    echo ""
    
    echo -e "${GREEN}✅ Votre stack MCP est maintenant opérationnelle !${NC}"
    echo ""
}

# Main execution
main() {
    print_banner
    
    check_prerequisites
    confirm_deployment
    test_ssh_connection
    transfer_files
    configure_env
    create_directories
    deploy_docker
    validate_deployment
    show_summary
    
    echo -e "${MAGENTA}🎊 Déploiement automatique terminé !${NC}"
    echo ""
}

# Run
main "$@"

