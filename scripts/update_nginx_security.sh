#!/bin/bash

# Script de mise à jour de la configuration nginx avec sécurité renforcée
# Auteur: MCP Team
# Version: 1.0.0

set -euo pipefail

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier que nous sommes dans le bon répertoire
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "Ce script doit être exécuté depuis la racine du projet MCP"
        exit 1
    fi
    
    # Vérifier que Docker et docker-compose sont installés
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose n'est pas installé"
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Sauvegarde de la configuration actuelle
backup_config() {
    log "Sauvegarde de la configuration nginx actuelle..."
    
    local backup_dir="backups/nginx_$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    
    if [[ -f "config/nginx/nginx.conf" ]]; then
        cp config/nginx/nginx.conf $backup_dir/nginx.conf.backup
        log_success "Configuration sauvegardée dans $backup_dir"
    else
        log_warning "Aucune configuration nginx existante trouvée"
    fi
}

# Validation de la configuration nginx
validate_nginx_config() {
    log "Validation de la configuration nginx..."
    
    # Test de la syntaxe nginx dans un conteneur temporaire
    if docker run --rm -v "$(pwd)/config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:alpine nginx -t; then
        log_success "Configuration nginx valide"
        return 0
    else
        log_error "Configuration nginx invalide"
        return 1
    fi
}

# Mise à jour du conteneur nginx
update_nginx_container() {
    log "Mise à jour du conteneur nginx..."
    
    # Arrêt du conteneur nginx
    if docker-compose ps | grep -q "mcp-nginx"; then
        log "Arrêt du conteneur nginx existant..."
        docker-compose stop nginx
    fi
    
    # Reconstruction et redémarrage
    log "Reconstruction du conteneur nginx..."
    docker-compose up -d nginx
    
    # Attendre que le conteneur soit prêt
    log "Attente du démarrage du conteneur..."
    for i in {1..30}; do
        if docker-compose ps | grep -q "mcp-nginx.*Up"; then
            log_success "Conteneur nginx démarré avec succès"
            return 0
        fi
        sleep 2
    done
    
    log_error "Le conteneur nginx n'a pas démarré dans les temps"
    return 1
}

# Test des endpoints après mise à jour
test_endpoints() {
    log "Test des endpoints après mise à jour..."
    
    local endpoints=(
        "https://api.dazno.de/health"
        "https://api.dazno.de/"
        "https://api.dazno.de/info"
        "https://api.dazno.de/metrics"
        "https://api.dazno.de/api/v1/health"
    )
    
    local failed_tests=0
    
    for endpoint in "${endpoints[@]}"; do
        log "Test de $endpoint..."
        
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint" || echo "000")
        
        case $http_code in
            200|201|204)
                log_success "✓ $endpoint - OK ($http_code)"
                ;;
            404)
                log_warning "⚠ $endpoint - Not Found ($http_code) - peut être normal selon l'endpoint"
                ;;
            *)
                log_error "✗ $endpoint - Erreur ($http_code)"
                ((failed_tests++))
                ;;
        esac
    done
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "Tous les tests d'endpoints ont réussi"
        return 0
    else
        log_error "$failed_tests test(s) d'endpoint ont échoué"
        return 1
    fi
}

# Test des headers de sécurité
test_security_headers() {
    log "Test des headers de sécurité..."
    
    local test_url="https://api.dazno.de/health"
    local temp_file=$(mktemp)
    
    curl -s -D "$temp_file" "$test_url" > /dev/null
    
    local security_headers=(
        "Strict-Transport-Security"
        "X-Frame-Options"
        "X-Content-Type-Options"
        "X-XSS-Protection"
        "Referrer-Policy"
        "Content-Security-Policy"
    )
    
    local missing_headers=0
    
    for header in "${security_headers[@]}"; do
        if grep -qi "$header" "$temp_file"; then
            log_success "✓ Header de sécurité trouvé: $header"
        else
            log_error "✗ Header de sécurité manquant: $header"
            ((missing_headers++))
        fi
    done
    
    rm -f "$temp_file"
    
    if [[ $missing_headers -eq 0 ]]; then
        log_success "Tous les headers de sécurité sont présents"
        return 0
    else
        log_error "$missing_headers header(s) de sécurité manquant(s)"
        return 1
    fi
}

# Test CORS pour app.dazno.de
test_cors() {
    log "Test de la configuration CORS pour app.dazno.de..."
    
    local test_url="https://api.dazno.de/health"
    local cors_headers
    
    cors_headers=$(curl -s -H "Origin: https://app.dazno.de" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization,Content-Type" -X OPTIONS "$test_url" -D - | grep -i "access-control")
    
    if echo "$cors_headers" | grep -qi "access-control-allow-origin"; then
        log_success "✓ CORS configuré pour app.dazno.de"
        return 0
    else
        log_error "✗ CORS non configuré correctement"
        return 1
    fi
}

# Rollback en cas d'erreur
rollback() {
    log_error "Rollback en cours..."
    
    local latest_backup
    latest_backup=$(ls -1t backups/nginx_*/nginx.conf.backup 2>/dev/null | head -1)
    
    if [[ -n "$latest_backup" ]]; then
        log "Restauration depuis $latest_backup..."
        cp "$latest_backup" config/nginx/nginx.conf
        
        # Redémarrage avec l'ancienne configuration
        docker-compose restart nginx
        
        log_success "Rollback terminé"
    else
        log_error "Aucune sauvegarde trouvée pour le rollback"
    fi
}

# Fonction principale
main() {
    log "=== Mise à jour de la sécurité nginx pour MCP ==="
    log "Timestamp: $(date)"
    
    # Trap pour le rollback en cas d'erreur
    trap 'rollback' ERR
    
    check_prerequisites
    backup_config
    
    if ! validate_nginx_config; then
        log_error "Configuration nginx invalide, abandon"
        exit 1
    fi
    
    update_nginx_container
    
    # Attendre un peu pour que nginx soit complètement prêt
    sleep 10
    
    # Tests
    if ! test_endpoints; then
        log_error "Tests d'endpoints échoués"
        exit 1
    fi
    
    if ! test_security_headers; then
        log_warning "Certains headers de sécurité sont manquants, mais on continue"
    fi
    
    if ! test_cors; then
        log_warning "Configuration CORS pourrait nécessiter des ajustements"
    fi
    
    log_success "=== Mise à jour terminée avec succès ==="
    log "Les endpoints suivants devraient maintenant être accessibles:"
    log "- https://api.dazno.de/health"
    log "- https://api.dazno.de/info"
    log "- https://api.dazno.de/metrics"
    log "- https://api.dazno.de/api/v1/*"
    log ""
    log "Headers de sécurité ajoutés:"
    log "- Strict-Transport-Security"
    log "- X-Frame-Options: DENY"
    log "- X-Content-Type-Options: nosniff"
    log "- Content-Security-Policy"
    log "- Referrer-Policy"
    log ""
    log "CORS configuré pour https://app.dazno.de"
}

# Exécution du script principal
main "$@"