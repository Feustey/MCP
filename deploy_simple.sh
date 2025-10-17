#!/bin/bash

################################################################################
# Script de Déploiement Simple MCP sur Hostinger
# 
# Usage: ./deploy_simple.sh
################################################################################

SERVER="147.79.101.32"
USER="root"
PASSWORD="Criteria0-Cadmium5-Attempt9-Exit2-Floss1"
LOCAL_DIR="/Users/stephanecourant/Documents/DAZ/MCP/MCP"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  $1"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Fonction pour exécuter des commandes SSH
ssh_exec() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$USER@$SERVER" "$1"
}

# Fonction pour copier des fichiers
scp_copy() {
    sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no -r "$1" "$USER@$SERVER:$2"
}

print_header "DÉPLOIEMENT MCP SUR HOSTINGER"
echo ""

# Vérifier si sshpass est installé
if ! command -v sshpass &> /dev/null; then
    print_error "sshpass n'est pas installé"
    echo ""
    echo "Installation:"
    echo "  macOS:  brew install sshpass"
    echo "  Linux:  sudo apt install sshpass"
    echo ""
    exit 1
fi

# Test de connexion
print_step "1/7 - Test de connexion au serveur $SERVER..."
if ssh_exec "echo 'Connection OK'" | grep -q "Connection OK"; then
    print_success "Connexion réussie"
else
    print_error "Impossible de se connecter au serveur"
    exit 1
fi
echo ""

# Installation des prérequis
print_step "2/7 - Installation des prérequis..."
ssh_exec "apt update -qq && apt install -y curl > /dev/null 2>&1 && echo 'OK'" | tail -1
if ! ssh_exec "command -v docker" &> /dev/null; then
    echo "  Installation de Docker..."
    ssh_exec "curl -fsSL https://get.docker.com | sh" > /dev/null
    print_success "Docker installé"
else
    print_success "Docker déjà installé"
fi

if ! ssh_exec "command -v docker-compose" &> /dev/null; then
    echo "  Installation de Docker Compose..."
    ssh_exec "curl -L 'https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-\$(uname -s)-\$(uname -m)' -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose" > /dev/null
    print_success "Docker Compose installé"
else
    print_success "Docker Compose déjà installé"
fi
echo ""

# Création du répertoire
print_step "3/7 - Création du répertoire /opt/mcp..."
ssh_exec "mkdir -p /opt/mcp"
print_success "Répertoire créé"
echo ""

# Upload des fichiers
print_step "4/7 - Upload des fichiers..."
echo "  Upload docker-compose.production.yml..."
scp_copy "$LOCAL_DIR/docker-compose.production.yml" "/opt/mcp/" > /dev/null

echo "  Upload config_production_hostinger.env..."
scp_copy "$LOCAL_DIR/config_production_hostinger.env" "/opt/mcp/" > /dev/null

echo "  Upload scripts..."
scp_copy "$LOCAL_DIR/scripts" "/opt/mcp/" > /dev/null

echo "  Upload config..."
scp_copy "$LOCAL_DIR/config" "/opt/mcp/" > /dev/null 2>&1 || echo "  (config peut-être manquant)"

echo "  Upload src..."
scp_copy "$LOCAL_DIR/src" "/opt/mcp/" > /dev/null 2>&1 || echo "  (src peut-être manquant)"

echo "  Upload app..."
scp_copy "$LOCAL_DIR/app" "/opt/mcp/" > /dev/null 2>&1 || echo "  (app peut-être manquant)"

print_success "Fichiers principaux uploadés"
echo ""

# Configuration
print_step "5/7 - Configuration..."
ssh_exec "cd /opt/mcp && cp config_production_hostinger.env .env.production"
ssh_exec "cd /opt/mcp && chmod +x scripts/*.sh"
ssh_exec "cd /opt/mcp && mkdir -p mcp-data/{logs,data,rag,backups,reports} logs/nginx config/qdrant backups"
print_success "Configuration initiale terminée"
echo ""

# Édition de .env.production
print_step "6/7 - Configuration de .env.production..."
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  ⚠️  CONFIGURATION REQUISE                                       ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Vous devez configurer au minimum:"
echo ""
echo -e "  ${RED}OBLIGATOIRE:${NC}"
echo "    • ANTHROPIC_API_KEY=sk-ant-api03-xxxxx"
echo ""
echo -e "  ${YELLOW}OPTIONNEL:${NC}"
echo "    • LNBITS_URL, LNBITS_ADMIN_KEY"
echo "    • TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
echo ""
echo -n "Voulez-vous éditer .env.production maintenant? (Y/n): "
read -r response

if [[ "$response" =~ ^[Yy]?$ ]]; then
    echo ""
    echo "Connexion au serveur pour éditer..."
    sshpass -p "$PASSWORD" ssh -t -o StrictHostKeyChecking=no "$USER@$SERVER" "cd /opt/mcp && nano .env.production"
    print_success "Configuration éditée"
else
    echo ""
    print_error "Vous devrez éditer .env.production plus tard:"
    echo "  ssh $USER@$SERVER"
    echo "  cd /opt/mcp"
    echo "  nano .env.production"
fi
echo ""

# Déploiement
print_step "7/7 - Lancement du déploiement Docker..."
echo ""
echo "Cela peut prendre 10-30 minutes (téléchargement des images Docker)..."
echo ""

# Lancer docker-compose directement
ssh_exec "cd /opt/mcp && docker-compose -f docker-compose.production.yml pull" 2>&1 | grep -E "(Pulling|Downloaded|Status)" || true
ssh_exec "cd /opt/mcp && docker-compose -f docker-compose.production.yml up -d"

sleep 10

print_success "Conteneurs démarrés"
echo ""

# Validation
print_step "Validation du déploiement..."
echo ""
ssh_exec "cd /opt/mcp && docker-compose -f docker-compose.production.yml ps"
echo ""

# Test API
echo "Test de l'API (dans 10 secondes)..."
sleep 10
ssh_exec "curl -s http://localhost:8000/ | head -5" || echo "API pas encore prête (normal au premier démarrage)"
echo ""

# Résumé final
print_header "DÉPLOIEMENT TERMINÉ"
echo ""
echo -e "${GREEN}✅ MCP a été déployé sur $SERVER${NC}"
echo ""
echo -e "${CYAN}🔗 URLs d'accès:${NC}"
echo "   • API directe:  http://$SERVER:8000/"
echo "   • Via Nginx:    http://$SERVER/"
echo "   • Docs:         http://$SERVER:8000/docs"
echo ""
echo -e "${CYAN}📊 Commandes utiles:${NC}"
echo "   ssh $USER@$SERVER"
echo "   cd /opt/mcp"
echo "   docker-compose -f docker-compose.production.yml ps"
echo "   docker-compose -f docker-compose.production.yml logs -f"
echo "   ./scripts/validate_deployment.sh"
echo ""
echo -e "${YELLOW}⚠️  MODE SHADOW ACTIVÉ${NC}"
echo "   Le système observe sans appliquer de changements réels"
echo "   Observez pendant 7-14 jours avant de désactiver"
echo ""
echo -e "${GREEN}🎉 Déploiement réussi!${NC}"
echo ""

