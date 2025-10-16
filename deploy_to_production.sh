#!/bin/bash
################################################################################
# Script de Déploiement Production Hostinger
#
# Transfère les fichiers et déploie la stack Docker sur le serveur de production
#
# Usage: ./deploy_to_production.sh
#
# Serveur: 147.79.101.32
# User: feustey
# Date: 13 octobre 2025
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REMOTE_HOST="147.79.101.32"
REMOTE_USER="feustey"
REMOTE_DIR="/home/feustey/mcp-production"
LOCAL_DIR="/Users/stephanecourant/Documents/DAZ/MCP/MCP"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║     🚀 DÉPLOIEMENT PRODUCTION HOSTINGER 🚀                ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

log_info "Serveur cible: ${REMOTE_USER}@${REMOTE_HOST}"
log_info "Répertoire distant: ${REMOTE_DIR}"
echo ""

# Étape 1 : Vérifier la connexion SSH
log_info "Étape 1/5 : Vérification de la connexion SSH..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes ${REMOTE_USER}@${REMOTE_HOST} echo "OK" &> /dev/null; then
    log_success "Connexion SSH OK"
else
    log_warning "Connexion SSH nécessite authentification"
    log_info "Vous serez invité à entrer votre mot de passe..."
fi

# Étape 2 : Créer le répertoire distant si nécessaire
log_info "Étape 2/5 : Préparation du répertoire distant..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_DIR}" || {
    log_error "Impossible de créer le répertoire distant"
    exit 1
}
log_success "Répertoire distant prêt"

# Étape 3 : Transférer les fichiers
log_info "Étape 3/5 : Transfert des fichiers (rsync)..."
log_info "Exclusions: venv*, __pycache__, .git, node_modules, *.log"

rsync -avz --progress \
    --exclude 'venv*' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '*.log' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude 'deployment_*.log' \
    --exclude 't4g-data' \
    --exclude 'mcp-data' \
    --exclude 'monitoring_data' \
    ${LOCAL_DIR}/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/ || {
    log_error "Échec du transfert rsync"
    exit 1
}

log_success "Fichiers transférés avec succès"

# Étape 4 : Déployer sur le serveur
log_info "Étape 4/5 : Déploiement Docker sur le serveur..."

ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
    set -e
    cd /home/feustey/mcp-production
    
    echo "📦 Installation de Docker si nécessaire..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        echo "✅ Docker installé"
    else
        echo "✅ Docker déjà installé"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo "✅ Docker Compose installé"
    else
        echo "✅ Docker Compose déjà installé"
    fi
    
    echo ""
    echo "🚀 Lancement de la stack Docker..."
    docker-compose -f docker-compose.hostinger.yml down || true
    docker-compose -f docker-compose.hostinger.yml build
    docker-compose -f docker-compose.hostinger.yml up -d
    
    echo ""
    echo "⏳ Attente de 30 secondes pour le démarrage..."
    sleep 30
    
    echo ""
    echo "📊 Status des containers:"
    docker-compose -f docker-compose.hostinger.yml ps
    
    echo ""
    echo "🧪 Test de l'API..."
    curl -s http://localhost:8000/ | head -20 || echo "⚠️  API pas encore prête"
    
    echo ""
    echo "✅ Déploiement terminé !"
ENDSSH

log_success "Déploiement Docker terminé"

# Étape 5 : Validation finale
log_info "Étape 5/5 : Validation du déploiement..."

echo ""
log_info "Connexion au serveur pour validation finale..."

ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
    cd /home/feustey/mcp-production
    
    echo "📊 Status final des containers:"
    docker ps --filter "name=mcp-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "🧪 Test de l'API (localhost:8000):"
    curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/
    
    echo ""
    echo "🔍 Logs récents de l'API:"
    docker logs mcp-api --tail=10
ENDSSH

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║           ✅ DÉPLOIEMENT RÉUSSI ! ✅                       ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

log_success "API accessible sur: http://${REMOTE_HOST}:8000"
log_success "Nginx accessible sur: http://${REMOTE_HOST}"
log_info ""
log_info "Prochaines étapes:"
log_info "  1. Configurer SSL: ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd ${REMOTE_DIR} && sudo certbot certonly --standalone -d api.dazno.de'"
log_info "  2. Configurer les backups automatiques"
log_info "  3. Configurer le monitoring"
log_info ""
log_success "🎉 Le système MCP est maintenant en production sur Hostinger !"

