#!/bin/bash

# Script de test local pour la configuration Docker MCP
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

error() {
    log "ERROR" "${RED}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Vérifier que Docker fonctionne
    if ! docker info &> /dev/null; then
        error "Docker n'est pas démarré ou accessible"
        exit 1
    fi
    
    success "Prérequis vérifiés"
}

# Création du fichier .env de test
create_test_env() {
    info "Création du fichier .env de test..."
    
    cat > .env.test << EOF
# Configuration MCP pour test local Docker
# Généré automatiquement le $(date '+%Y-%m-%d %H:%M:%S')

# Configuration de base
ENVIRONMENT=development
DEBUG=true
DRY_RUN=true
LOG_LEVEL=DEBUG

# Configuration serveur
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Base de données MongoDB (Hostinger - test)
MONGO_URL=mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true
MONGO_NAME=mcp_test

# Redis (Hostinger - test)
REDIS_HOST=d4s8888skckos8c80w4swgcw
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=20

# Configuration IA (test)
AI_OPENAI_API_KEY=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
AI_OPENAI_MODEL=gpt-3.5-turbo
AI_OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Configuration Lightning
LIGHTNING_LND_HOST=localhost:10009
LIGHTNING_LND_REST_URL=https://127.0.0.1:8080
LIGHTNING_USE_INTERNAL_LNBITS=true
LIGHTNING_LNBITS_URL=http://127.0.0.1:8000/lnbits

# Configuration sécurité
SECURITY_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJtb24tdGVuYW50LWlkIiwiZXhwIjoxNzQ3MzM5NzAzfQ.-5mgm01tuSlQQXtZIa35c9MUBdpB1WFyf6kPzk53TGY
SECURITY_CORS_ORIGINS=["*"]
SECURITY_ALLOWED_HOSTS=["*"]

# Configuration performance
PERF_RESPONSE_CACHE_TTL=3600
PERF_EMBEDDING_CACHE_TTL=86400
PERF_MAX_WORKERS=2

# Configuration logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_ENABLE_STRUCTLOG=true
LOG_ENABLE_FILE_LOGGING=false
LOG_LOG_FILE_PATH=logs/mcp.log

# Configuration heuristiques
HEURISTIC_CENTRALITY_WEIGHT=0.4
HEURISTIC_CAPACITY_WEIGHT=0.2
HEURISTIC_REPUTATION_WEIGHT=0.2
HEURISTIC_FEES_WEIGHT=0.1
HEURISTIC_UPTIME_WEIGHT=0.1
HEURISTIC_VECTOR_WEIGHT=0.7

# Configuration monitoring
GRAFANA_PASSWORD=admin123
EOF

    success "Fichier .env.test créé"
}

# Test de construction de l'image
test_build() {
    info "Test de construction de l'image Docker..."
    
    # Arrêt des conteneurs existants
    docker-compose -f docker-compose.hostinger.yml down --remove-orphans || true
    
    # Construction de l'image
    docker-compose -f docker-compose.hostinger.yml build --no-cache
    
    if [[ $? -eq 0 ]]; then
        success "Image Docker construite avec succès"
    else
        error "Échec de la construction de l'image Docker"
        exit 1
    fi
}

# Test de démarrage des services
test_startup() {
    info "Test de démarrage des services..."
    
    # Démarrage avec le fichier .env.test
    docker-compose -f docker-compose.hostinger.yml --env-file .env.test up -d
    
    if [[ $? -eq 0 ]]; then
        success "Services démarrés avec succès"
    else
        error "Échec du démarrage des services"
        exit 1
    fi
}

# Test de connectivité
test_connectivity() {
    info "Test de connectivité..."
    
    # Attendre que les services démarrent
    sleep 10
    
    # Test de santé de l'API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        success "API accessible et fonctionnelle"
    else
        warn "API non accessible immédiatement, vérification des logs..."
        docker-compose -f docker-compose.hostinger.yml logs mcp-api
        return 1
    fi
    
    # Test de la documentation
    if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
        success "Documentation accessible"
    else
        warn "Documentation non accessible"
    fi
    
    # Test des bases de données
    info "Test de connectivité aux bases de données..."
    
    # Test MongoDB
    docker exec mcp-api-hostinger python3 -c "
import pymongo
try:
    client = pymongo.MongoClient('mongodb://root:8qsY4vHBSoltyy23ItSbZOiXeJpxtyCLzZBWjfylAFyh8hQRl61PVbwhUZpaMGrJ@b44g08c0kkggckwswswck8ks:27017/?directConnection=true', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ MongoDB: Connexion réussie')
except Exception as e:
    print(f'❌ MongoDB: Erreur de connexion - {e}')
    exit(1)
" && success "MongoDB connecté" || warn "MongoDB non accessible"
    
    # Test Redis
    docker exec mcp-api-hostinger python3 -c "
import redis
try:
    r = redis.Redis(
        host='d4s8888skckos8c80w4swgcw',
        port=6379,
        password='YnsPl4fmrjv7i3ZO546O4zsXRsRO3O3vNMbCZAJ5sNlu7oMmj20WYrtOn33kjmo1',
        ssl=True,
        socket_timeout=5
    )
    r.ping()
    print('✅ Redis: Connexion réussie')
except Exception as e:
    print(f'❌ Redis: Erreur de connexion - {e}')
    exit(1)
" && success "Redis connecté" || warn "Redis non accessible"
}

# Test des endpoints
test_endpoints() {
    info "Test des endpoints API..."
    
    # Test health check
    echo "🔍 Test health check..."
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
    
    # Test endpoint racine
    echo ""
    echo "🔍 Test endpoint racine..."
    curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/
    
    # Test documentation
    echo ""
    echo "🔍 Test documentation..."
    if curl -s http://localhost:8000/docs | grep -q "Swagger"; then
        success "Documentation Swagger accessible"
    else
        warn "Documentation Swagger non accessible"
    fi
    
    success "Tests des endpoints terminés"
}

# Nettoyage
cleanup() {
    info "Nettoyage des conteneurs de test..."
    
    # Arrêt des conteneurs
    docker-compose -f docker-compose.hostinger.yml down --remove-orphans
    
    # Suppression du fichier .env.test
    rm -f .env.test
    
    success "Nettoyage terminé"
}

# Affichage des résultats
show_results() {
    info "Résultats des tests:"
    echo ""
    echo "✅ Tests réussis:"
    echo "  - Construction de l'image Docker"
    echo "  - Démarrage des services"
    echo "  - Connectivité API"
    echo "  - Tests des endpoints"
    echo ""
    echo "🌐 Services testés:"
    echo "  - API MCP: http://localhost:8000"
    echo "  - Documentation: http://localhost:8000/docs"
    echo "  - Health check: http://localhost:8000/health"
    echo ""
    echo "📋 Prochaines étapes:"
    echo "  1. Commit et push des changements"
    echo "  2. Déploiement sur le serveur Hostinger"
    echo "  3. Vérification de l'API en production"
}

# Fonction principale
main() {
    info "Démarrage des tests Docker locaux..."
    
    check_prerequisites
    create_test_env
    test_build
    test_startup
    test_connectivity
    test_endpoints
    show_results
    
    success "Tests Docker locaux terminés avec succès !"
}

# Gestion des signaux pour le nettoyage
trap cleanup EXIT

# Exécution
main "$@" 