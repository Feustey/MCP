#!/bin/bash

# Script de vérification rapide des endpoints MCP
# Auteur: MCP Team
# Version: 1.0.0

set -euo pipefail

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="https://api.dazno.de"
TIMEOUT=10

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
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

# Test d'un endpoint
test_endpoint() {
    local endpoint="$1"
    local expected_codes="${2:-200,201,204}"
    local method="${3:-GET}"
    local headers="${4:-}"
    
    local full_url="${API_URL}${endpoint}"
    local curl_opts="-s --max-time $TIMEOUT -w %{http_code}:%{time_total} -o /dev/null"
    
    if [[ -n "$headers" ]]; then
        curl_opts="$curl_opts $headers"
    fi
    
    local result
    result=$(curl $curl_opts -X "$method" "$full_url" 2>/dev/null || echo "000:0")
    
    local http_code="${result%:*}"
    local response_time="${result#*:}"
    
    # Vérifier si le code de retour est attendu
    if [[ ",$expected_codes," == *",$http_code,"* ]]; then
        log_success "$endpoint - $http_code (${response_time}s)"
        return 0
    else
        log_error "$endpoint - $http_code (${response_time}s) - attendu: $expected_codes"
        return 1
    fi
}

# Test des headers de sécurité
test_security_headers() {
    local endpoint="$1"
    local full_url="${API_URL}${endpoint}"
    
    log "Test des headers de sécurité pour $endpoint"
    
    local temp_file=$(mktemp)
    curl -s -D "$temp_file" "$full_url" > /dev/null 2>&1 || true
    
    local security_headers=(
        "Strict-Transport-Security"
        "X-Frame-Options"
        "X-Content-Type-Options"
        "X-XSS-Protection"
        "Referrer-Policy"
    )
    
    local found_headers=0
    local total_headers=${#security_headers[@]}
    
    for header in "${security_headers[@]}"; do
        if grep -qi "$header" "$temp_file"; then
            ((found_headers++))
        fi
    done
    
    rm -f "$temp_file"
    
    if [[ $found_headers -eq $total_headers ]]; then
        log_success "Headers de sécurité: $found_headers/$total_headers"
        return 0
    else
        log_warning "Headers de sécurité: $found_headers/$total_headers"
        return 1
    fi
}

# Test CORS
test_cors() {
    local endpoint="$1"
    local origin="${2:-https://app.dazno.de}"
    
    log "Test CORS pour $endpoint avec origin $origin"
    
    local headers_opts="-H 'Origin: $origin' -H 'Access-Control-Request-Method: GET'"
    local result
    result=$(curl -s -X OPTIONS --max-time $TIMEOUT -w "%{http_code}" -o /dev/null $headers_opts "${API_URL}${endpoint}" 2>/dev/null || echo "000")
    
    if [[ "$result" == "200" || "$result" == "204" ]]; then
        log_success "CORS OK pour $endpoint"
        return 0
    else
        log_error "CORS KO pour $endpoint - code: $result"
        return 1
    fi
}

# Test SSL/TLS
test_ssl() {
    log "Test de la configuration SSL/TLS"
    
    local ssl_info
    ssl_info=$(openssl s_client -connect api.dazno.de:443 -servername api.dazno.de </dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "ERROR")
    
    if [[ "$ssl_info" != "ERROR" ]]; then
        log_success "Certificat SSL valide"
        echo "$ssl_info" | sed 's/^/    /'
        return 0
    else
        log_error "Problème avec le certificat SSL"
        return 1
    fi
}

# Fonction principale
main() {
    echo "================================================================"
    echo "     Vérification des endpoints MCP pour app.dazno.de"
    echo "================================================================"
    echo "API URL: $API_URL"
    echo "Timestamp: $(date)"
    echo ""
    
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # Liste des endpoints à tester
    local endpoints=(
        "/health:200"
        "/:200"
        "/info:200"
        "/metrics:200,404"
        "/api/v1/health:200,404"
        "/api/v1/:200,404"
        "/api/v1/rag/health:200,404"
        "/docs:200,404"
    )
    
    echo "=== Tests d'accessibilité des endpoints ==="
    for endpoint_config in "${endpoints[@]}"; do
        local endpoint="${endpoint_config%:*}"
        local expected_codes="${endpoint_config#*:}"
        
        ((total_tests++))
        if test_endpoint "$endpoint" "$expected_codes"; then
            ((passed_tests++))
        else
            ((failed_tests++))
        fi
    done
    
    echo ""
    echo "=== Tests de sécurité ==="
    
    # Test SSL
    ((total_tests++))
    if test_ssl; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    
    # Test headers de sécurité
    ((total_tests++))
    if test_security_headers "/health"; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    
    # Test CORS
    ((total_tests++))
    if test_cors "/health"; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    
    echo ""
    echo "================================================================"
    echo "                        RÉSUMÉ"
    echo "================================================================"
    echo "Total des tests: $total_tests"
    echo "Tests réussis: $passed_tests"
    echo "Tests échoués: $failed_tests"
    
    if [[ $failed_tests -eq 0 ]]; then
        echo ""
        log_success "🎉 Tous les tests sont passés ! L'API est prête pour app.dazno.de"
        exit 0
    else
        echo ""
        log_error "❌ $failed_tests test(s) ont échoué"
        echo ""
        echo "Actions recommandées:"
        echo "1. Vérifier que le déploiement est terminé"
        echo "2. Exécuter le script de mise à jour: ./scripts/update_nginx_security.sh"
        echo "3. Vérifier les logs nginx: docker-compose logs nginx"
        echo "4. Redémarrer les services si nécessaire: docker-compose restart"
        exit 1
    fi
}

# Gestion des options
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            API_URL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--url API_URL] [--timeout SECONDS]"
            echo ""
            echo "Options:"
            echo "  --url URL        URL de base de l'API (défaut: https://api.dazno.de)"
            echo "  --timeout SEC    Timeout en secondes (défaut: 10)"
            echo "  --help           Affiche cette aide"
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
    esac
done

# Exécution
main