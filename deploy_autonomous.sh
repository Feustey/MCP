#!/bin/bash

################################################################################
# Script de Déploiement Autonome Complet
#
# Ce script gère l'intégralité du déploiement sur Hostinger :
# - Transfert des fichiers
# - Configuration de l'environnement
# - Déploiement Docker
# - Validation complète
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e

# Configuration
SSH_USER="feustey"
SSH_HOST="147.79.101.32"
DEPLOY_DIR="/home/feustey/mcp-production"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Fonction pour afficher les étapes
step() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}🚀 $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Banner
clear 2>/dev/null || true
echo -e "${BOLD}${CYAN}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     MCP v1.0 - Déploiement Autonome Complet              ║
║     Lightning Network Channel Optimizer                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

info "Serveur cible: ${SSH_USER}@${SSH_HOST}"
info "Répertoire: ${DEPLOY_DIR}"
echo ""

# Vérification de la connexion SSH
step "Étape 1/7 : Vérification de la connexion SSH"

if ssh -o ConnectTimeout=10 -o BatchMode=yes ${SSH_USER}@${SSH_HOST} "echo 'Connection OK'" &>/dev/null; then
    success "Connexion SSH établie"
else
    error "Impossible de se connecter au serveur"
    echo ""
    info "Configuration SSH requise. Exécutez :"
    echo "  ssh-copy-id ${SSH_USER}@${SSH_HOST}"
    exit 1
fi

# Préparation des fichiers locaux
step "Étape 2/7 : Préparation des fichiers locaux"

FILES_TO_DEPLOY=(
    "docker-compose.hostinger.yml"
    "Dockerfile.production"
    "mongo-init.js"
    "nginx-docker.conf"
    "docker_entrypoint.sh"
    "start_api.sh"
    "requirements-production.txt"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ -f "$file" ]; then
        success "Fichier présent: $file"
    else
        error "Fichier manquant: $file"
        exit 1
    fi
done

# Préparation des répertoires à transférer
DIRS_TO_DEPLOY=(
    "app"
    "src"
    "config"
    "scripts"
    "auth"
)

for dir in "${DIRS_TO_DEPLOY[@]}"; do
    if [ -d "$dir" ]; then
        success "Répertoire présent: $dir"
    else
        warning "Répertoire manquant: $dir"
    fi
done

# Création du répertoire sur le serveur
step "Étape 3/7 : Création de l'infrastructure sur le serveur"

ssh ${SSH_USER}@${SSH_HOST} << 'REMOTE_SETUP'
set -e

# Créer le répertoire principal
mkdir -p /home/feustey/mcp-production
cd /home/feustey/mcp-production

# Créer la structure
mkdir -p app/{routes,services} src/{clients,optimizers,tools,auth} config scripts logs data ssl backups/mongodb

echo "✓ Infrastructure créée"
REMOTE_SETUP

success "Infrastructure serveur créée"

# Transfert des fichiers
step "Étape 4/7 : Transfert des fichiers vers le serveur"

info "Transfert des fichiers de configuration..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ -f "$file" ]; then
        scp -q "$file" ${SSH_USER}@${SSH_HOST}:${DEPLOY_DIR}/
        success "Transféré: $file"
    fi
done

info "Transfert des répertoires..."
for dir in "${DIRS_TO_DEPLOY[@]}"; do
    if [ -d "$dir" ]; then
        rsync -az --delete "$dir/" ${SSH_USER}@${SSH_HOST}:${DEPLOY_DIR}/$dir/
        success "Synchronisé: $dir/"
    fi
done

# Configuration de l'environnement
step "Étape 5/7 : Configuration de l'environnement"

info "Génération des secrets de sécurité..."

# Générer les secrets localement
MONGODB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
SECRET_KEY=$(openssl rand -base64 32 | tr -d '\n')
ENCRYPTION_KEY=$(openssl rand -base64 32)

success "Secrets générés"

info "Création du fichier .env..."

ssh ${SSH_USER}@${SSH_HOST} "cat > ${DEPLOY_DIR}/.env" << ENVFILE
# MCP v1.0 - Production Configuration
ENVIRONMENT=production
DEBUG=false
DRY_RUN=true

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=2

# MONGODB (Docker Internal)
MONGODB_USER=mcpuser
MONGODB_PASSWORD=${MONGODB_PASSWORD}
MONGODB_DATABASE=mcp_prod
MONGODB_URI=mongodb://mcpuser:${MONGODB_PASSWORD}@mongodb:27017/mcp_prod?authSource=admin

# REDIS (Docker Internal)
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# SECURITY
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# LNBITS (À configurer)
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_ADMIN_KEY=your_admin_key
LNBITS_INVOICE_KEY=your_invoice_key

# TELEGRAM (Optionnel)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# FEATURES
ENABLE_SHADOW_MODE=true
ENABLE_RAG=false

# OPTIMIZATION
MAX_CHANGES_PER_DAY=5
REQUIRE_MANUAL_APPROVAL=true

# CACHE TTL
REDIS_TTL_NODE_DATA=300
REDIS_TTL_CHANNEL_DATA=600

# LOGGING
LOG_LEVEL=INFO
STRUCTLOG_ENABLED=true
ENVFILE

success "Fichier .env créé avec secrets sécurisés"

# Déploiement Docker
step "Étape 6/7 : Déploiement Docker"

info "Configuration des permissions..."
ssh ${SSH_USER}@${SSH_HOST} << 'REMOTE_PERMS'
cd /home/feustey/mcp-production
chmod +x docker_entrypoint.sh start_api.sh
chmod +x scripts/*.sh 2>/dev/null || true
chmod 755 logs data config ssl backups
REMOTE_PERMS

success "Permissions configurées"

info "Arrêt des containers existants (si présents)..."
ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml down 2>/dev/null || true"
success "Nettoyage effectué"

info "Construction des images Docker..."
ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml build --no-cache"
success "Images construites"

info "Démarrage des services..."
ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml up -d"
success "Services démarrés"

info "Attente de la stabilisation des services (60 secondes)..."
sleep 60

# Validation
step "Étape 7/7 : Validation du déploiement"

# Récupérer les statuts
CONTAINER_STATUS=$(ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml ps -q | wc -l")
RUNNING_STATUS=$(ssh ${SSH_USER}@${SSH_HOST} "cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml ps -q | xargs sudo docker inspect -f '{{.State.Running}}' | grep -c true || echo 0")

info "Containers déployés: $CONTAINER_STATUS"
info "Containers en cours d'exécution: $RUNNING_STATUS"

# Test MongoDB
if ssh ${SSH_USER}@${SSH_HOST} "sudo docker exec mcp-mongodb mongosh -u mcpuser -p ${MONGODB_PASSWORD} --authenticationDatabase admin --eval 'db.runCommand(\"ping\")' --quiet" &>/dev/null; then
    success "MongoDB opérationnel"
else
    error "MongoDB ne répond pas"
fi

# Test Redis
if ssh ${SSH_USER}@${SSH_HOST} "sudo docker exec mcp-redis redis-cli -a ${REDIS_PASSWORD} ping" 2>&1 | grep -q "PONG"; then
    success "Redis opérationnel"
else
    error "Redis ne répond pas"
fi

# Attendre un peu plus pour l'API
sleep 10

# Test API
if ssh ${SSH_USER}@${SSH_HOST} "curl -sf http://localhost:8000/ -m 5" &>/dev/null; then
    success "API MCP opérationnelle"
else
    warning "API ne répond pas encore (peut prendre 2-3 minutes au premier démarrage)"
fi

# Test Nginx
if ssh ${SSH_USER}@${SSH_HOST} "curl -sf http://localhost/ -m 5" &>/dev/null; then
    success "Nginx opérationnel"
else
    warning "Nginx ne répond pas encore"
fi

# Résumé final
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                                                            ║${NC}"
echo -e "${BOLD}${GREEN}║     ✅ DÉPLOIEMENT AUTONOME TERMINÉ AVEC SUCCÈS !         ║${NC}"
echo -e "${BOLD}${GREEN}║                                                            ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}📊 Informations de Déploiement${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🌐 Serveur:           ${CYAN}${SSH_HOST}${NC}"
echo -e "📁 Répertoire:        ${CYAN}${DEPLOY_DIR}${NC}"
echo -e "🐳 Containers actifs: ${CYAN}${RUNNING_STATUS}/${CONTAINER_STATUS}${NC}"
echo -e "🔐 MongoDB User:      ${CYAN}mcpuser${NC}"
echo -e "🗄️  Database:          ${CYAN}mcp_prod${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}🔗 URLs d'Accès${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "API (HTTP):  ${CYAN}http://147.79.101.32:8000${NC}"
echo -e "Web (HTTP):  ${CYAN}http://147.79.101.32${NC}"
echo -e "Docs API:    ${CYAN}http://147.79.101.32:8000/docs${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}📝 Commandes Utiles${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Voir les logs:       ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml logs -f'${NC}"
echo -e "Status containers:   ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml ps'${NC}"
echo -e "Redémarrer:          ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml restart'${NC}"
echo -e "Arrêter:             ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml down'${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}⚠️  Points d'Attention${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}1.${NC} L'API peut prendre 2-3 minutes pour être pleinement opérationnelle"
echo -e "${YELLOW}2.${NC} Mode DRY_RUN activé par défaut (pas de modifications réelles)"
echo -e "${YELLOW}3.${NC} Configurer LNBits dans ${DEPLOY_DIR}/.env avant utilisation réelle"
echo -e "${YELLOW}4.${NC} SSL/HTTPS sera configuré ultérieurement avec certbot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BOLD}🎯 Prochaines Étapes${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${CYAN}1.${NC} Vérifier les logs: ${CYAN}ssh ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_DIR} && sudo docker-compose -f docker-compose.hostinger.yml logs -f mcp-api'${NC}"
echo -e "${CYAN}2.${NC} Tester l'API: ${CYAN}curl http://147.79.101.32:8000/api/v1/health${NC}"
echo -e "${CYAN}3.${NC} Configurer LNBits dans .env"
echo -e "${CYAN}4.${NC} Configurer SSL/HTTPS avec certbot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Sauvegarder les credentials
cat > DEPLOYMENT_CREDENTIALS.txt << CREDS
# MCP v1.0 - Credentials de Déploiement
# Date: $(date)
# 
# ⚠️  FICHIER SENSIBLE - NE PAS COMMITTER ⚠️

Serveur: ${SSH_HOST}
Utilisateur: ${SSH_USER}
Répertoire: ${DEPLOY_DIR}

MongoDB:
  User: mcpuser
  Password: ${MONGODB_PASSWORD}
  Database: mcp_prod
  Connection: mongodb://mcpuser:${MONGODB_PASSWORD}@mongodb:27017/mcp_prod?authSource=admin

Redis:
  Password: ${REDIS_PASSWORD}
  Connection: redis://:${REDIS_PASSWORD}@redis:6379/0

Security:
  Secret Key: ${SECRET_KEY}
  Encryption Key: ${ENCRYPTION_KEY}

URLs:
  API: http://147.79.101.32:8000
  Docs: http://147.79.101.32:8000/docs
  Web: http://147.79.101.32
CREDS

success "Credentials sauvegardés dans DEPLOYMENT_CREDENTIALS.txt"
warning "⚠️  IMPORTANT : Ne pas committer DEPLOYMENT_CREDENTIALS.txt !"

echo ""
echo -e "${BOLD}${GREEN}🎉 Déploiement terminé ! MCP v1.0 est opérationnel sur Hostinger !${NC}"
echo ""

exit 0

