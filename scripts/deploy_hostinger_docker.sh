#!/bin/bash

################################################################################
# Script de Déploiement Hostinger avec Docker
#
# Déploie MCP v1.0 sur Hostinger avec MongoDB et Redis intégrés dans Docker
#
# Usage:
#   ./scripts/deploy_hostinger_docker.sh
#
# Options:
#   --skip-build    Skip Docker build
#   --skip-ssl      Skip SSL configuration
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SKIP_BUILD=false
SKIP_SSL=false
COMPOSE_FILE="docker-compose.hostinger.yml"
ENV_FILE=".env"
PROJECT_DIR=$(pwd)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        *)
            echo "Usage: $0 [--skip-build] [--skip-ssl]"
            exit 1
            ;;
    esac
done

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
show_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║        MCP v1.0 - Déploiement Docker Hostinger            ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Fichiers requis
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Fichier $COMPOSE_FILE introuvable"
        exit 1
    fi
    
    if [ ! -f "mongo-init.js" ]; then
        log_error "Fichier mongo-init.js introuvable"
        exit 1
    fi
    
    if [ ! -f "nginx-docker.conf" ]; then
        log_error "Fichier nginx-docker.conf introuvable"
        exit 1
    fi
    
    log_success "Tous les prérequis sont satisfaits"
}

# Vérifier/créer .env
setup_environment() {
    log_info "Configuration de l'environnement..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.hostinger" ]; then
            log_info "Copie de .env.hostinger vers .env"
            cp .env.hostinger .env
        else
            log_error "Fichier .env ou .env.hostinger introuvable"
            log_info "Créez le fichier .env avec les credentials nécessaires"
            exit 1
        fi
    fi
    
    # Vérifier que les variables critiques sont configurées
    source .env
    
    if [[ "${SECRET_KEY}" == *"CHANGEZ"* ]] || [[ "${ENCRYPTION_KEY}" == *"CHANGEZ"* ]]; then
        log_error "⚠️  Les clés de sécurité n'ont pas été changées dans .env !"
        log_info ""
        log_info "Générez-les avec:"
        log_info "  python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        log_info "  python3 -c \"import base64, os; print(base64.b64encode(os.urandom(32)).decode())\""
        log_info ""
        read -p "Continuer quand même ? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    log_success "Environnement configuré"
}

# Créer les répertoires nécessaires
create_directories() {
    log_info "Création des répertoires..."
    
    mkdir -p logs data config ssl backups/mongodb
    
    log_success "Répertoires créés"
}

# Builder les images Docker
build_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Build Docker skippé (--skip-build)"
        return
    fi
    
    log_info "Build des images Docker..."
    
    docker-compose -f "$COMPOSE_FILE" build
    
    log_success "Images buildées"
}

# Arrêter les services existants
stop_existing_services() {
    log_info "Arrêt des services existants..."
    
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" down
        log_success "Services arrêtés"
    else
        log_info "Aucun service en cours d'exécution"
    fi
}

# Démarrer les services
start_services() {
    log_info "Démarrage des services Docker..."
    
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services démarrés"
}

# Attendre que les services soient prêts
wait_for_services() {
    log_info "Attente de la disponibilité des services..."
    
    local max_wait=120  # 2 minutes
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            log_success "Services opérationnels"
            return 0
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    
    echo ""
    log_warning "Timeout atteint, vérification manuelle requise"
}

# Valider le déploiement
validate_deployment() {
    log_info "Validation du déploiement..."
    
    # Vérifier les containers
    log_info "Vérification des containers..."
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Test MongoDB
    log_info "Test MongoDB..."
    if docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')" &> /dev/null; then
        log_success "MongoDB opérationnel"
    else
        log_error "MongoDB ne répond pas"
    fi
    
    # Test Redis
    log_info "Test Redis..."
    if docker exec mcp-redis redis-cli ping &> /dev/null; then
        log_success "Redis opérationnel"
    else
        log_error "Redis ne répond pas"
    fi
    
    # Test API
    log_info "Test API..."
    sleep 5  # Laisser l'API démarrer
    if curl -sf http://localhost:8000/ > /dev/null; then
        log_success "API opérationnelle"
    else
        log_warning "API ne répond pas encore (peut prendre quelques secondes)"
    fi
    
    # Test Nginx
    log_info "Test Nginx..."
    if curl -sf http://localhost/ > /dev/null; then
        log_success "Nginx opérationnel"
    else
        log_warning "Nginx ne répond pas"
    fi
}

# Configurer SSL avec Let's Encrypt
setup_ssl() {
    if [ "$SKIP_SSL" = true ]; then
        log_warning "Configuration SSL skippée (--skip-ssl)"
        return
    fi
    
    log_info "Configuration SSL Let's Encrypt..."
    
    # Vérifier que certbot est installé
    if ! command -v certbot &> /dev/null; then
        log_info "Installation de certbot..."
        apt-get update
        apt-get install -y certbot
    fi
    
    # Obtenir le certificat
    log_info "Obtention du certificat SSL..."
    
    if certbot certonly --standalone \
        -d api.dazno.de \
        --agree-tos \
        --email admin@dazno.de \
        --non-interactive; then
        
        # Copier les certificats
        cp /etc/letsencrypt/live/api.dazno.de/fullchain.pem ssl/
        cp /etc/letsencrypt/live/api.dazno.de/privkey.pem ssl/
        
        log_success "Certificat SSL installé"
        log_info "Décommentez la section HTTPS dans nginx-docker.conf et redémarrez Nginx"
    else
        log_warning "Échec de l'obtention du certificat SSL"
        log_info "Vous pouvez le configurer manuellement plus tard"
    fi
}

# Afficher le résumé
show_summary() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              Déploiement Terminé !                         ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ Services déployés:"
    echo "   - MongoDB (port 27017, local uniquement)"
    echo "   - Redis (port 6379, local uniquement)"
    echo "   - MCP API (port 8000, local uniquement)"
    echo "   - Nginx (ports 80/443, public)"
    echo ""
    echo "🔗 URLs:"
    echo "   - API directe:    http://localhost:8000/"
    echo "   - Via Nginx:      http://localhost/"
    echo "   - Documentation:  http://localhost/docs"
    echo ""
    echo "📊 Commandes utiles:"
    echo "   - Logs:           docker-compose -f $COMPOSE_FILE logs -f"
    echo "   - Status:         docker-compose -f $COMPOSE_FILE ps"
    echo "   - Restart:        docker-compose -f $COMPOSE_FILE restart"
    echo "   - Stop:           docker-compose -f $COMPOSE_FILE down"
    echo ""
    echo "💾 Backup MongoDB:"
    echo "   - Manuel:         ./scripts/backup_mongodb_docker.sh"
    echo "   - Crontab:        0 2 * * * $PROJECT_DIR/scripts/backup_mongodb_docker.sh"
    echo ""
    echo "🔒 SSL:"
    if [ "$SKIP_SSL" = true ]; then
        echo "   - Skippé, à configurer manuellement"
    else
        echo "   - Certificat installé dans ssl/"
        echo "   - Décommentez HTTPS dans nginx-docker.conf"
    fi
    echo ""
}

# Main execution
main() {
    show_banner
    check_prerequisites
    setup_environment
    create_directories
    build_images
    stop_existing_services
    start_services
    wait_for_services
    validate_deployment
    setup_ssl
    show_summary
    
    log_success "🎉 Déploiement terminé avec succès !"
}

# Run
main "$@"

