#!/bin/bash

################################################################################
# Script de Validation Post-Déploiement MCP
#
# Valide que tous les services sont opérationnels après déploiement
#
# Usage:
#   ./scripts/validate_deployment.sh
#
# Auteur: MCP Team
# Date: 16 octobre 2025
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
DOMAIN="api.dazno.de"
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNING=0

# Functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((TESTS_WARNING++))
}

show_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║        MCP - Validation Post-Déploiement                  ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

# Test 1: Docker Compose running
test_docker_compose() {
    log_test "1. Vérification des conteneurs Docker"
    
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        local running=$(docker-compose -f "$COMPOSE_FILE" ps | grep -c "Up" || echo "0")
        log_pass "Conteneurs en cours d'exécution: $running"
    else
        log_fail "Aucun conteneur en cours d'exécution"
        return 1
    fi
    
    # Check individual containers
    local containers=("mcp-api-prod" "mcp-nginx-prod" "mcp-mongodb-prod" "mcp-redis-prod" "mcp-qdrant-prod" "mcp-ollama")
    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            log_pass "  ↳ $container: Running"
        else
            log_fail "  ↳ $container: Not running"
        fi
    done
    
    echo ""
}

# Test 2: API Health
test_api_health() {
    log_test "2. Vérification de l'API MCP"
    
    # Test local
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_pass "API health endpoint (localhost:8000)"
    elif curl -sf http://localhost:8000/ > /dev/null 2>&1; then
        log_pass "API root endpoint (localhost:8000)"
    else
        log_fail "API ne répond pas sur localhost:8000"
    fi
    
    # Test response time
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/ 2>/dev/null || echo "999")
    if (( $(echo "$response_time < 2" | bc -l) )); then
        log_pass "  ↳ Temps de réponse: ${response_time}s (< 2s)"
    else
        log_warn "  ↳ Temps de réponse: ${response_time}s (> 2s)"
    fi
    
    echo ""
}

# Test 3: Nginx
test_nginx() {
    log_test "3. Vérification de Nginx"
    
    # Test HTTP
    if curl -sf http://localhost/ > /dev/null 2>&1; then
        log_pass "Nginx HTTP (localhost)"
    else
        log_fail "Nginx ne répond pas sur HTTP"
    fi
    
    # Test HTTPS si domaine accessible
    if curl -sf "https://$DOMAIN/" > /dev/null 2>&1; then
        log_pass "Nginx HTTPS ($DOMAIN)"
    else
        log_warn "HTTPS non accessible sur $DOMAIN (normal si pas encore configuré)"
    fi
    
    # Check SSL certificate
    if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        local expiry=$(sudo openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" 2>/dev/null | cut -d= -f2)
        log_pass "  ↳ Certificat SSL présent (expire: $expiry)"
    else
        log_warn "  ↳ Certificat SSL non trouvé"
    fi
    
    echo ""
}

# Test 4: MongoDB Local
test_mongodb() {
    log_test "4. Vérification de MongoDB Local"
    
    if docker exec mcp-mongodb-prod mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null | grep -q "ok"; then
        log_pass "MongoDB health check"
        
        # Check authentication
        if docker exec mcp-mongodb-prod mongosh \
            --username mcp_admin \
            --password mcp_secure_password_2025 \
            --authenticationDatabase admin \
            --quiet --eval "db.runCommand({ connectionStatus: 1 })" 2>/dev/null | grep -q "ok"; then
            log_pass "  ↳ Authentification OK"
        else
            log_warn "  ↳ Problème d'authentification"
        fi
        
        # Check database exists
        if docker exec mcp-mongodb-prod mongosh \
            --username mcp_admin \
            --password mcp_secure_password_2025 \
            --authenticationDatabase admin \
            --quiet --eval "db.getMongo().getDBNames()" 2>/dev/null | grep -q "mcp_prod"; then
            log_pass "  ↳ Database mcp_prod créée"
        else
            log_warn "  ↳ Database mcp_prod non trouvée (sera créée au premier usage)"
        fi
    else
        log_fail "MongoDB ne répond pas"
    fi
    
    echo ""
}

# Test 5: Redis Local
test_redis() {
    log_test "5. Vérification de Redis Local"
    
    if docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 ping 2>/dev/null | grep -q "PONG"; then
        log_pass "Redis health check"
        
        # Test write/read
        if docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 SET test_key "test_value" 2>/dev/null > /dev/null; then
            if docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 GET test_key 2>/dev/null | grep -q "test_value"; then
                log_pass "  ↳ Read/Write OK"
                docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 DEL test_key 2>/dev/null > /dev/null
            else
                log_warn "  ↳ Problème de lecture"
            fi
        else
            log_warn "  ↳ Problème d'écriture"
        fi
        
        # Check persistence
        local rdb_status=$(docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 CONFIG GET save 2>/dev/null | tail -1)
        if [ -n "$rdb_status" ]; then
            log_pass "  ↳ Persistence configurée"
        fi
    else
        log_fail "Redis ne répond pas"
    fi
    
    echo ""
}

# Test 6: Qdrant
test_qdrant() {
    log_test "6. Vérification de Qdrant (Vector DB)"
    
    if docker exec mcp-qdrant-prod curl -sf http://localhost:6333/health > /dev/null 2>&1; then
        log_pass "Qdrant health check"
        
        # Check collections
        local collections=$(docker exec mcp-qdrant-prod curl -s http://localhost:6333/collections 2>/dev/null | grep -o '"name":"[^"]*"' | wc -l)
        log_pass "  ↳ Collections: $collections"
    else
        log_fail "Qdrant ne répond pas"
    fi
    
    echo ""
}

# Test 7: Ollama
test_ollama() {
    log_test "7. Vérification de Ollama (LLM)"
    
    if docker exec mcp-ollama wget -q --spider http://localhost:11434/api/tags 2>/dev/null; then
        log_pass "Ollama service actif"
        
        # Check models
        local models=$(docker exec mcp-ollama ollama list 2>/dev/null | tail -n +2 | wc -l)
        if [ "$models" -gt 0 ]; then
            log_pass "  ↳ Modèles installés: $models"
            docker exec mcp-ollama ollama list 2>/dev/null | tail -n +2 | while read -r line; do
                echo "      • $(echo $line | awk '{print $1}')"
            done
        else
            log_warn "  ↳ Aucun modèle installé"
        fi
    else
        log_fail "Ollama ne répond pas"
    fi
    
    echo ""
}

# Test 8: Environment Configuration
test_environment() {
    log_test "8. Vérification de la configuration"
    
    if [ -f ".env.production" ]; then
        log_pass "Fichier .env.production présent"
        
        # Check critical variables
        source .env.production
        
        if [ "$DRY_RUN" = "true" ]; then
            log_pass "  ↳ Mode Shadow activé (DRY_RUN=true)"
        else
            log_warn "  ↳ Mode Shadow DÉSACTIVÉ (modifications réelles)"
        fi
        
        if [ "$ENVIRONMENT" = "production" ]; then
            log_pass "  ↳ ENVIRONMENT=production"
        else
            log_warn "  ↳ ENVIRONMENT=$ENVIRONMENT (attendu: production)"
        fi
        
        # Check MongoDB Local
        if [[ "$MONGO_URL" =~ "mongodb://mcp_admin" ]]; then
            log_pass "  ↳ MongoDB Local configuré"
        else
            log_warn "  ↳ MongoDB URL non configuré (attendu: mongodb://mcp_admin...)"
        fi
        
        # Check Redis Local
        if [[ "$REDIS_URL" =~ "redis://:mcp_redis_password" ]]; then
            log_pass "  ↳ Redis Local configuré"
        else
            log_warn "  ↳ Redis URL non configuré (attendu: redis://:mcp_redis_password...)"
        fi
        
    else
        log_fail "Fichier .env.production manquant"
    fi
    
    echo ""
}

# Test 9: Logs
test_logs() {
    log_test "9. Vérification des logs"
    
    if [ -d "mcp-data/logs" ]; then
        log_pass "Répertoire mcp-data/logs présent"
        
        # Check for errors in recent logs
        if docker logs mcp-api-prod 2>&1 | tail -50 | grep -qi "error"; then
            local errors=$(docker logs mcp-api-prod 2>&1 | tail -50 | grep -ic "error")
            log_warn "  ↳ $errors erreurs dans les derniers logs"
        else
            log_pass "  ↳ Aucune erreur dans les derniers logs"
        fi
    else
        log_warn "Répertoire mcp-data/logs manquant"
    fi
    
    echo ""
}

# Test 10: Network Connectivity
test_network() {
    log_test "10. Vérification de la connectivité réseau"
    
    # Test MongoDB connection from API
    if docker exec mcp-api-prod python3 -c "import os; from pymongo import MongoClient; client = MongoClient(os.getenv('MONGO_URL'), serverSelectionTimeoutMS=5000); client.server_info()" 2>/dev/null; then
        log_pass "Connexion MongoDB depuis API OK"
    else
        log_warn "Connexion MongoDB depuis API échouée (vérifier MONGO_URL)"
    fi
    
    # Test Redis connection
    if docker exec mcp-api-prod python3 -c "import os; import redis; r = redis.from_url(os.getenv('REDIS_URL'), socket_connect_timeout=5); r.ping()" 2>/dev/null; then
        log_pass "Connexion Redis OK"
    else
        log_warn "Connexion Redis échouée (vérifier REDIS_URL)"
    fi
    
    echo ""
}

# Test 11: Disk Space
test_disk_space() {
    log_test "11. Vérification de l'espace disque"
    
    local disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$disk_usage" -lt 80 ]; then
        log_pass "Espace disque: ${disk_usage}% utilisé"
    elif [ "$disk_usage" -lt 90 ]; then
        log_warn "Espace disque: ${disk_usage}% utilisé (attention)"
    else
        log_fail "Espace disque: ${disk_usage}% utilisé (critique)"
    fi
    
    # Docker volumes
    local docker_volumes=$(docker system df -v | grep "VOLUME NAME" -A 100 | tail -n +2 | wc -l)
    log_pass "  ↳ Volumes Docker: $docker_volumes"
    
    echo ""
}

# Test 12: Security
test_security() {
    log_test "12. Vérification de la sécurité"
    
    # Check file permissions
    if [ -f ".env.production" ]; then
        local perms=$(stat -c "%a" .env.production 2>/dev/null || stat -f "%A" .env.production 2>/dev/null)
        if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
            log_pass "Permissions .env.production correctes ($perms)"
        else
            log_warn "Permissions .env.production: $perms (recommandé: 600)"
        fi
    fi
    
    # Check if firewall is active
    if command -v ufw &> /dev/null; then
        if sudo ufw status | grep -q "Status: active"; then
            log_pass "Firewall UFW actif"
        else
            log_warn "Firewall UFW inactif"
        fi
    fi
    
    echo ""
}

# Summary
show_summary() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              Résumé de la Validation                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}✓ Tests réussis:${NC}     $TESTS_PASSED"
    echo -e "${RED}✗ Tests échoués:${NC}     $TESTS_FAILED"
    echo -e "${YELLOW}⚠ Avertissements:${NC}   $TESTS_WARNING"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 Déploiement validé avec succès !${NC}"
        echo ""
        echo "Prochaines étapes:"
        echo "  1. Vérifier les logs: docker-compose -f $COMPOSE_FILE logs -f"
        echo "  2. Tester l'API: curl https://$DOMAIN/api/v1/health"
        echo "  3. Observer en mode shadow pendant 7-14 jours"
        echo "  4. Configurer le monitoring: python3 monitor_production.py"
        return 0
    else
        echo -e "${RED}⚠️  Déploiement incomplet - $TESTS_FAILED test(s) échoué(s)${NC}"
        echo ""
        echo "Actions recommandées:"
        echo "  1. Vérifier les logs: docker-compose -f $COMPOSE_FILE logs"
        echo "  2. Vérifier la configuration: cat .env.production"
        echo "  3. Redémarrer les services: docker-compose -f $COMPOSE_FILE restart"
        return 1
    fi
}

# Main
main() {
    show_banner
    
    test_docker_compose
    test_api_health
    test_nginx
    test_mongodb
    test_redis
    test_qdrant
    test_ollama
    test_environment
    test_logs
    test_network
    test_disk_space
    test_security
    
    show_summary
}

main "$@"

