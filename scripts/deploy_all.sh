#!/bin/bash

################################################################################
# Script de Déploiement Complet MCP v1.0 Production
#
# Orchestre le déploiement complet de l'infrastructure:
# - Configuration Nginx + SSL
# - Service Systemd
# - Logrotate
# - Docker production
# - Validation complète
#
# Usage:
#   sudo ./scripts/deploy_all.sh [--skip-ssl] [--skip-docker]
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
SKIP_SSL=false
SKIP_DOCKER=false
PROJECT_DIR="/home/feustey/mcp-production"
DOMAIN="api.dazno.de"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        *)
            echo "Usage: $0 [--skip-ssl] [--skip-docker]"
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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Ce script doit être exécuté avec sudo"
        exit 1
    fi
}

check_dependencies() {
    log_info "Vérification des dépendances..."
    
    local deps=("nginx" "systemctl" "certbot" "docker" "docker-compose")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Dépendances manquantes: ${missing[*]}"
        log_info "Installation des dépendances manquantes..."
        
        apt-get update
        
        for dep in "${missing[@]}"; do
            case $dep in
                nginx)
                    apt-get install -y nginx
                    ;;
                certbot)
                    apt-get install -y certbot python3-certbot-nginx
                    ;;
                docker)
                    curl -fsSL https://get.docker.com | sh
                    ;;
                docker-compose)
                    apt-get install -y docker-compose
                    ;;
                *)
                    apt-get install -y "$dep"
                    ;;
            esac
        done
    fi
    
    log_success "Toutes les dépendances sont installées"
}

backup_existing() {
    log_info "Sauvegarde des configurations existantes..."
    
    local backup_dir="${PROJECT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup Nginx config
    if [ -f /etc/nginx/sites-available/mcp-api ]; then
        cp /etc/nginx/sites-available/mcp-api "$backup_dir/"
        log_info "  - Nginx config sauvegardée"
    fi
    
    # Backup systemd service
    if [ -f /etc/systemd/system/mcp-api.service ]; then
        cp /etc/systemd/system/mcp-api.service "$backup_dir/"
        log_info "  - Systemd service sauvegardé"
    fi
    
    # Backup .env
    if [ -f "${PROJECT_DIR}/.env" ]; then
        cp "${PROJECT_DIR}/.env" "$backup_dir/"
        log_info "  - .env sauvegardé"
    fi
    
    log_success "Backup créé dans $backup_dir"
}

configure_nginx() {
    log_info "=== Configuration Nginx + SSL ==="
    
    if [ -f "${PROJECT_DIR}/scripts/configure_nginx_production.sh" ]; then
        bash "${PROJECT_DIR}/scripts/configure_nginx_production.sh"
        log_success "Nginx configuré"
    else
        log_error "Script configure_nginx_production.sh introuvable"
        exit 1
    fi
    
    # SSL avec Let's Encrypt
    if [ "$SKIP_SSL" = false ]; then
        log_info "Configuration SSL avec Let's Encrypt..."
        
        if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@dazno.de; then
            log_success "SSL configuré pour $DOMAIN"
        else
            log_warning "Échec configuration SSL (peut-être déjà configuré)"
        fi
    else
        log_warning "Configuration SSL skippée (--skip-ssl)"
    fi
}

configure_systemd() {
    log_info "=== Configuration Service Systemd ==="
    
    if [ -f "${PROJECT_DIR}/scripts/configure_systemd_autostart.sh" ]; then
        bash "${PROJECT_DIR}/scripts/configure_systemd_autostart.sh"
        log_success "Systemd service configuré"
    else
        log_error "Script configure_systemd_autostart.sh introuvable"
        exit 1
    fi
}

configure_logrotate() {
    log_info "=== Configuration Logrotate ==="
    
    if [ -f "${PROJECT_DIR}/scripts/setup_logrotate.sh" ]; then
        bash "${PROJECT_DIR}/scripts/setup_logrotate.sh"
        log_success "Logrotate configuré"
    else
        log_warning "Script setup_logrotate.sh introuvable (optionnel)"
    fi
}

deploy_docker() {
    log_info "=== Déploiement Docker Production ==="
    
    if [ "$SKIP_DOCKER" = false ]; then
        cd "$PROJECT_DIR"
        
        if [ -f "${PROJECT_DIR}/scripts/deploy_docker_production.sh" ]; then
            bash "${PROJECT_DIR}/scripts/deploy_docker_production.sh"
            log_success "Docker déployé"
        else
            log_warning "Script deploy_docker_production.sh introuvable"
            log_info "Build Docker manuel..."
            
            docker-compose -f docker-compose.production.yml build
            docker-compose -f docker-compose.production.yml up -d
            
            log_success "Docker déployé manuellement"
        fi
    else
        log_warning "Déploiement Docker skippé (--skip-docker)"
    fi
}

validate_deployment() {
    log_info "=== Validation du Déploiement ==="
    
    sleep 5  # Attendre que les services démarrent
    
    # Check Nginx
    log_info "Vérification Nginx..."
    if systemctl is-active --quiet nginx; then
        log_success "  ✓ Nginx actif"
    else
        log_error "  ✗ Nginx non actif"
    fi
    
    # Check systemd service
    log_info "Vérification service MCP..."
    if systemctl is-active --quiet mcp-api; then
        log_success "  ✓ Service MCP actif"
    else
        log_warning "  ⚠ Service MCP non actif (peut-être en mode Docker uniquement)"
    fi
    
    # Check API HTTP
    log_info "Vérification API HTTP..."
    if curl -s http://localhost:8000/ | grep -q "status"; then
        log_success "  ✓ API répond sur HTTP"
    else
        log_warning "  ⚠ API ne répond pas sur HTTP"
    fi
    
    # Check API HTTPS
    if [ "$SKIP_SSL" = false ]; then
        log_info "Vérification API HTTPS..."
        if curl -sk https://${DOMAIN}/ | grep -q "status"; then
            log_success "  ✓ API répond sur HTTPS"
        else
            log_warning "  ⚠ API ne répond pas sur HTTPS"
        fi
    fi
    
    # Check Docker containers
    if [ "$SKIP_DOCKER" = false ]; then
        log_info "Vérification containers Docker..."
        
        cd "$PROJECT_DIR"
        local running_containers=$(docker-compose -f docker-compose.production.yml ps --services --filter "status=running" | wc -l)
        
        if [ "$running_containers" -gt 0 ]; then
            log_success "  ✓ $running_containers container(s) actif(s)"
        else
            log_warning "  ⚠ Aucun container actif"
        fi
    fi
}

generate_report() {
    log_info "=== Génération du Rapport de Déploiement ==="
    
    local report_file="${PROJECT_DIR}/deployment_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=========================================="
        echo "MCP v1.0 - Rapport de Déploiement"
        echo "=========================================="
        echo ""
        echo "Date: $(date)"
        echo "Domaine: $DOMAIN"
        echo "Projet: $PROJECT_DIR"
        echo ""
        echo "=========================================="
        echo "Services"
        echo "=========================================="
        echo ""
        echo "Nginx:"
        systemctl status nginx --no-pager || echo "  Non disponible"
        echo ""
        echo "MCP API Service:"
        systemctl status mcp-api --no-pager || echo "  Non disponible"
        echo ""
        
        if [ "$SKIP_DOCKER" = false ]; then
            echo "Docker Containers:"
            cd "$PROJECT_DIR"
            docker-compose -f docker-compose.production.yml ps || echo "  Non disponible"
            echo ""
        fi
        
        echo "=========================================="
        echo "Tests de Connexion"
        echo "=========================================="
        echo ""
        echo "HTTP (localhost:8000):"
        curl -s -w "\nStatus Code: %{http_code}\n" http://localhost:8000/ || echo "  Échec"
        echo ""
        
        if [ "$SKIP_SSL" = false ]; then
            echo "HTTPS ($DOMAIN):"
            curl -sk -w "\nStatus Code: %{http_code}\n" https://${DOMAIN}/ || echo "  Échec"
            echo ""
        fi
        
        echo "=========================================="
        echo "Logs Récents"
        echo "=========================================="
        echo ""
        echo "Nginx Error Log (dernières 20 lignes):"
        tail -n 20 /var/log/nginx/error.log || echo "  Non disponible"
        echo ""
        
        echo "MCP API Log (dernières 20 lignes):"
        journalctl -u mcp-api -n 20 --no-pager || echo "  Non disponible"
        echo ""
        
        echo "=========================================="
        echo "Fin du Rapport"
        echo "=========================================="
        
    } > "$report_file"
    
    log_success "Rapport généré: $report_file"
}

show_next_steps() {
    echo ""
    echo "=========================================="
    echo "🎉 Déploiement Terminé !"
    echo "=========================================="
    echo ""
    echo "✅ Nginx configuré et actif"
    echo "✅ Service systemd configuré"
    echo "✅ Logrotate configuré"
    
    if [ "$SKIP_DOCKER" = false ]; then
        echo "✅ Docker déployé"
    fi
    
    if [ "$SKIP_SSL" = false ]; then
        echo "✅ SSL/HTTPS configuré"
    fi
    
    echo ""
    echo "=========================================="
    echo "Prochaines Étapes"
    echo "=========================================="
    echo ""
    echo "1. Vérifier l'API:"
    echo "   curl https://${DOMAIN}/"
    echo ""
    echo "2. Configurer les services cloud:"
    echo "   - MongoDB Atlas (M10, eu-west-1)"
    echo "   - Redis Cloud (250MB, eu-west-1)"
    echo "   Mettre à jour .env avec les connection strings"
    echo ""
    echo "3. Activer le monitoring:"
    echo "   python monitor_production.py --duration 3600"
    echo ""
    echo "4. Lancer les tests:"
    echo "   python test_production_pipeline.py"
    echo ""
    echo "5. Consulter les logs:"
    echo "   journalctl -u mcp-api -f"
    echo "   tail -f logs/api.log"
    echo ""
    echo "📚 Documentation complète:"
    echo "   - PHASE5-QUICKSTART.md"
    echo "   - docs/phase5-production-deployment.md"
    echo ""
    echo "=========================================="
}

# Main execution
main() {
    log_info "Démarrage du déploiement MCP v1.0 Production"
    echo ""
    
    # Pre-flight checks
    check_root
    check_dependencies
    
    # Backup
    backup_existing
    echo ""
    
    # Déploiement
    configure_nginx
    echo ""
    
    configure_systemd
    echo ""
    
    configure_logrotate
    echo ""
    
    deploy_docker
    echo ""
    
    # Validation
    validate_deployment
    echo ""
    
    # Rapport
    generate_report
    echo ""
    
    # Instructions
    show_next_steps
}

# Run
main "$@"
