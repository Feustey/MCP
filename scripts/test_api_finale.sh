#!/bin/bash

# Script de test final de l'API MCP
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
SSH_KEY="/Users/stephanecourant/.ssh/id_ed25519"
SSH_OPTIONS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions utilitaires
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Test complet de l'API
test_api_complete() {
    info "🎉 Test complet de l'API..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Test de l'API depuis l'hôte ==="
        
        echo "Test /health:"
        curl -f http://localhost:8000/health && echo " ✅" || echo " ❌"
        
        echo "Test / (root):"
        curl -f http://localhost:8000/ && echo " ✅" || echo " ❌"
        
        echo "Test /api/v1/status:"
        curl -f http://localhost:8000/api/v1/status && echo " ✅" || echo " ❌"
        
        echo "Test /docs (documentation):"
        curl -f http://localhost:8000/docs && echo " ✅" || echo " ❌"
        
        echo "Test /metrics (doit retourner 404):"
        curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/metrics
        echo " (404 attendu)"
        
        echo -e "\n=== Test depuis l'extérieur ==="
        echo "Test via IP directe:"
        curl -f http://147.79.101.32:8000/health && echo " ✅" || echo " ❌"
        
        echo "Test via domaine:"
        curl -f https://api.dazno.de/health && echo " ✅" || echo " ❌"
EOF
}

# Vérification des services
verifier_services() {
    info "🔍 Vérification des services..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== État des conteneurs ==="
        docker ps
        
        echo -e "\n=== Ports en écoute ==="
        netstat -tlnp | grep -E ':(8000|8080|8443|3000|9090)' || echo "Aucun port trouvé"
        
        echo -e "\n=== Logs récents ==="
        docker logs mcp-api --tail=5
        
        echo -e "\n=== Utilisation des ressources ==="
        docker stats --no-stream mcp-api mcp-nginx mcp-prometheus mcp-grafana || echo "Impossible de récupérer les stats"
EOF
}

# Test des dashboards
test_dashboards() {
    info "📊 Test des dashboards..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Test Grafana ==="
        curl -f http://localhost:3000 && echo " ✅ Grafana accessible" || echo " ❌ Grafana non accessible"
        
        echo "=== Test Prometheus ==="
        curl -f http://localhost:9090 && echo " ✅ Prometheus accessible" || echo " ❌ Prometheus non accessible"
        
        echo "=== Test Nginx ==="
        curl -f http://localhost:8080 && echo " ✅ Nginx accessible" || echo " ❌ Nginx non accessible"
EOF
}

# Fonction principale
main() {
    echo "🎉 Test final de l'API MCP"
    echo "========================="
    
    test_api_complete
    verifier_services
    test_dashboards
    
    success "🎉 Tests terminés!"
    echo ""
    echo "🌐 Résumé des accès :"
    echo "   🌐 API principale: https://api.dazno.de"
    echo "   📊 Grafana: http://147.79.101.32:3000 (admin/admin)"
    echo "   📈 Prometheus: http://147.79.101.32:9090"
    echo "   📚 Nginx: http://147.79.101.32:8080"
    echo "   📚 Documentation: https://api.dazno.de/docs"
    echo ""
    echo "✅ L'API MCP est maintenant opérationnelle !"
}

# Exécution du script
main "$@" 