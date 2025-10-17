#!/bin/bash

################################################################################
# Script de Déploiement Unifié MCP sur Hostinger
#
# Ce script prépare et déploie MCP v1.0 en production sur Hostinger avec:
# - Docker Compose
# - MongoDB Atlas + Redis Upstash (cloud)
# - Ollama + Qdrant (local dans Docker)
# - Nginx + SSL Let's Encrypt
# - Mode Shadow activé par défaut
#
# Usage:
#   ./deploy_to_hostinger.sh [OPTIONS]
#
# Options:
#   --skip-docker       Skip Docker rebuild
#   --skip-ssl          Skip SSL configuration
#   --skip-ollama-pull  Skip Ollama model download
#   --help              Show this help
#
# Auteur: MCP Team
# Date: 16 octobre 2025
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SKIP_DOCKER=false
SKIP_SSL=false
SKIP_OLLAMA_PULL=false
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
PROJECT_DIR="/opt/mcp"
DOMAIN="api.dazno.de"
EMAIL="admin@dazno.de"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-ollama-pull)
            SKIP_OLLAMA_PULL=true
            shift
            ;;
        --help)
            grep '^#' "$0" | tail -n +3 | head -n -1 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "${MAGENTA}[STEP]${NC} $1"
}

# Banner
show_banner() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║        ${GREEN}MCP v1.0 - Déploiement Production Hostinger${CYAN}       ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Vérifier les prérequis
check_prerequisites() {
    log_step "1/9 - Vérification des prérequis"
    echo "=================================================="
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        log_info "Installation: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    log_success "Docker installé: $(docker --version | cut -d' ' -f3)"
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
    log_success "Docker Compose installé"
    
    # Nginx
    if ! command -v nginx &> /dev/null; then
        log_warning "Nginx n'est pas installé, l'installer maintenant"
        sudo apt update && sudo apt install -y nginx
    fi
    log_success "Nginx installé"
    
    # Fichiers requis
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Fichier $COMPOSE_FILE introuvable"
        exit 1
    fi
    log_success "Fichier docker-compose présent"
    
    echo ""
}

# Vérifier/créer .env
setup_environment() {
    log_step "2/9 - Configuration de l'environnement"
    echo "=================================================="
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "config_production_hostinger.env" ]; then
            log_info "Copie de config_production_hostinger.env vers $ENV_FILE"
            cp config_production_hostinger.env "$ENV_FILE"
            log_warning "⚠️  Veuillez éditer $ENV_FILE et configurer:"
            log_warning "   - MONGO_URL (MongoDB Atlas)"
            log_warning "   - REDIS_URL (Upstash Redis)"
            log_warning "   - LNBITS_URL et LNBITS_ADMIN_KEY"
            log_warning "   - ANTHROPIC_API_KEY"
            log_warning "   - TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID"
            echo ""
            read -p "Appuyez sur Entrée quand c'est fait, ou Ctrl+C pour annuler..."
        else
            log_error "Fichier $ENV_FILE ou config_production_hostinger.env introuvable"
            log_info "Créez le fichier $ENV_FILE avec les credentials nécessaires"
            exit 1
        fi
    fi
    
    log_success "Fichier $ENV_FILE présent"
    
    # Vérifier que DRY_RUN est activé
    if grep -q "DRY_RUN=true" "$ENV_FILE"; then
        log_success "Mode Shadow activé (DRY_RUN=true) ✓"
    else
        log_warning "⚠️  Mode Shadow non activé - recommandé pour le premier déploiement"
        read -p "Activer le mode Shadow ? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            sed -i.bak 's/DRY_RUN=false/DRY_RUN=true/' "$ENV_FILE"
            log_success "Mode Shadow activé"
        fi
    fi
    
    echo ""
}

# Créer les répertoires nécessaires
create_directories() {
    log_step "3/9 - Création des répertoires"
    echo "=================================================="
    
    mkdir -p mcp-data/{logs,data,rag,backups,reports}
    mkdir -p logs/nginx
    mkdir -p config/qdrant
    mkdir -p config/nginx
    mkdir -p backups
    mkdir -p ssl
    
    log_success "Répertoires créés"
    echo ""
}

# Configuration Nginx
configure_nginx() {
    log_step "4/9 - Configuration Nginx"
    echo "=================================================="
    
    if [ "$SKIP_SSL" = true ]; then
        log_warning "Configuration SSL skippée (--skip-ssl)"
    else
        log_info "Exécution du script de configuration Nginx..."
        if [ -f "scripts/configure_nginx_production.sh" ]; then
            sudo bash scripts/configure_nginx_production.sh
            log_success "Nginx configuré"
        else
            log_warning "Script configure_nginx_production.sh introuvable, skip"
        fi
    fi
    
    echo ""
}

# Configuration SSL Let's Encrypt
setup_ssl() {
    if [ "$SKIP_SSL" = true ]; then
        log_warning "Configuration SSL skippée (--skip-ssl)"
        return
    fi
    
    log_step "5/9 - Configuration SSL Let's Encrypt"
    echo "=================================================="
    
    # Vérifier que certbot est installé
    if ! command -v certbot &> /dev/null; then
        log_info "Installation de certbot..."
        sudo apt update
        sudo apt install -y certbot python3-certbot-nginx
    fi
    
    # Vérifier si le certificat existe déjà
    if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        log_success "Certificat SSL déjà présent pour $DOMAIN"
    else
        log_info "Obtention du certificat SSL pour $DOMAIN..."
        
        if sudo certbot --nginx -d "$DOMAIN" --agree-tos --email "$EMAIL" --non-interactive; then
            log_success "Certificat SSL obtenu et installé"
        else
            log_warning "Échec de l'obtention du certificat SSL"
            log_info "Vous pouvez le configurer manuellement plus tard avec:"
            log_info "  sudo certbot --nginx -d $DOMAIN"
        fi
    fi
    
    echo ""
}

# Arrêter les services existants
stop_existing_services() {
    log_step "6/9 - Arrêt des services existants"
    echo "=================================================="
    
    if docker-compose -f "$COMPOSE_FILE" ps 2>/dev/null | grep -q "Up"; then
        log_info "Arrêt des conteneurs..."
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Services arrêtés"
    else
        log_info "Aucun service en cours d'exécution"
    fi
    
    echo ""
}

# Build et démarrage des services
start_services() {
    log_step "7/9 - Démarrage des services Docker"
    echo "=================================================="
    
    if [ "$SKIP_DOCKER" = false ]; then
        log_info "Pull des images Docker..."
        docker-compose -f "$COMPOSE_FILE" pull 2>/dev/null || true
    else
        log_warning "Build Docker skippé (--skip-docker)"
    fi
    
    log_info "Démarrage des conteneurs..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services démarrés"
    echo ""
    
    log_info "Attente du démarrage complet (30 secondes)..."
    sleep 30
    echo ""
}

# Initialiser Ollama
setup_ollama() {
    if [ "$SKIP_OLLAMA_PULL" = true ]; then
        log_warning "Téléchargement des modèles Ollama skippé (--skip-ollama-pull)"
        return
    fi
    
    log_step "8/9 - Initialisation Ollama"
    echo "=================================================="
    
    log_info "Vérification du service Ollama..."
    if docker ps | grep -q "mcp-ollama"; then
        log_success "Service Ollama en cours d'exécution"
        
        log_info "Téléchargement des modèles (peut prendre 30-60 min pour llama3:70b)..."
        log_warning "Vous pouvez commencer avec llama3:8b si vous voulez un démarrage rapide"
        
        echo ""
        read -p "Télécharger llama3:70b maintenant ? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            log_info "Téléchargement de llama3:70b-instruct-2025-07-01..."
            docker exec mcp-ollama ollama pull llama3:70b-instruct-2025-07-01 || {
                log_warning "Échec du téléchargement de llama3:70b"
                log_info "Essai avec llama3:8b à la place..."
                docker exec mcp-ollama ollama pull llama3:8b-instruct
            }
        else
            log_info "Téléchargement de llama3:8b (plus rapide)..."
            docker exec mcp-ollama ollama pull llama3:8b-instruct
        fi
        
        log_info "Téléchargement du modèle d'embeddings..."
        docker exec mcp-ollama ollama pull nomic-embed-text
        
        log_success "Modèles Ollama installés"
    else
        log_warning "Service Ollama non trouvé, skip"
    fi
    
    echo ""
}

# Valider le déploiement
validate_deployment() {
    log_step "9/9 - Validation du déploiement"
    echo "=================================================="
    
    # Status des containers
    log_info "Status des conteneurs:"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    # Test API
    log_info "Test de l'API..."
    sleep 5
    
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_success "API opérationnelle (http://localhost:8000)"
    elif curl -sf http://localhost:8000/ > /dev/null 2>&1; then
        log_success "API opérationnelle (http://localhost:8000)"
    else
        log_warning "API ne répond pas encore (peut prendre quelques minutes)"
    fi
    
    # Test Nginx
    if curl -sf http://localhost/ > /dev/null 2>&1; then
        log_success "Nginx opérationnel (http://localhost)"
    else
        log_warning "Nginx ne répond pas"
    fi
    
    # Test HTTPS
    if [ "$SKIP_SSL" = false ]; then
        if curl -sf "https://$DOMAIN/" > /dev/null 2>&1; then
            log_success "HTTPS opérationnel (https://$DOMAIN)"
        else
            log_warning "HTTPS non accessible (certificat peut-être en cours de génération)"
        fi
    fi
    
    # Test Qdrant
    if docker exec mcp-qdrant-prod curl -sf http://localhost:6333/health > /dev/null 2>&1; then
        log_success "Qdrant opérationnel"
    else
        log_warning "Qdrant ne répond pas"
    fi
    
    # Test Ollama
    if docker exec mcp-ollama wget -q --spider http://localhost:11434/api/tags 2>/dev/null; then
        log_success "Ollama opérationnel"
    else
        log_warning "Ollama ne répond pas"
    fi
    
    echo ""
}

# Afficher le résumé
show_summary() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}              ${GREEN}✓ Déploiement Terminé !${NC}                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✅ Services déployés:${NC}"
    echo "   - MCP API (port 8000)"
    echo "   - Nginx (ports 80/443)"
    echo "   - Qdrant Vector DB (port 6333)"
    echo "   - Ollama LLM (port 11434)"
    echo ""
    echo -e "${BLUE}🔗 URLs d'accès:${NC}"
    echo "   - API directe:       http://localhost:8000/"
    echo "   - Via Nginx (HTTP):  http://localhost/"
    if [ "$SKIP_SSL" = false ]; then
        echo "   - Via Nginx (HTTPS): https://$DOMAIN/"
    fi
    echo "   - Documentation:     https://$DOMAIN/docs"
    echo "   - Health check:      https://$DOMAIN/api/v1/health"
    echo ""
    echo -e "${YELLOW}⚠️  MODE SHADOW ACTIVÉ:${NC}"
    echo "   Le système observe et recommande mais N'APPLIQUE PAS les changements"
    echo "   Période recommandée: 7-14 jours d'observation"
    echo "   Pour désactiver: éditer $ENV_FILE et mettre DRY_RUN=false"
    echo ""
    echo -e "${MAGENTA}📊 Commandes utiles:${NC}"
    echo "   - Logs:              docker-compose -f $COMPOSE_FILE logs -f"
    echo "   - Status:            docker-compose -f $COMPOSE_FILE ps"
    echo "   - Restart:           docker-compose -f $COMPOSE_FILE restart"
    echo "   - Stop:              docker-compose -f $COMPOSE_FILE down"
    echo "   - Monitoring:        python3 monitor_production.py"
    echo ""
    echo -e "${CYAN}📚 Documentation:${NC}"
    echo "   - Guide complet:     DEPLOY_HOSTINGER_PRODUCTION.md"
    echo "   - Phase 5 Status:    PHASE5-STATUS.md"
    echo "   - Roadmap:           _SPECS/Roadmap-Production-v1.0.md"
    echo ""
    echo -e "${GREEN}🎉 Prochaines étapes:${NC}"
    echo "   1. Vérifier les logs: docker-compose -f $COMPOSE_FILE logs -f mcp-api"
    echo "   2. Tester l'API:      curl https://$DOMAIN/api/v1/health"
    echo "   3. Observer 7-14j en mode shadow"
    echo "   4. Analyser les rapports dans mcp-data/reports/"
    echo "   5. Désactiver DRY_RUN après validation"
    echo ""
}

# Main execution
main() {
    show_banner
    check_prerequisites
    setup_environment
    create_directories
    configure_nginx
    setup_ssl
    stop_existing_services
    start_services
    setup_ollama
    validate_deployment
    show_summary
    
    log_success "🎉 Déploiement terminé avec succès !"
    echo ""
}

# Run
main "$@"

