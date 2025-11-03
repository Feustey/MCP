#!/bin/bash
# fix_mcp_issues.sh - Correction complète des problèmes MCP

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           MCP - CORRECTION DES PROBLÈMES                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Vérifier que Docker est en cours d'exécution
if ! docker ps > /dev/null 2>&1; then
    error "Docker n'est pas en cours d'exécution"
    exit 1
fi

# Vérifier que les services MCP sont démarrés
if ! docker-compose -f docker-compose.hostinger.yml ps | grep -q "Up"; then
    warning "Services MCP non démarrés, démarrage..."
    docker-compose -f docker-compose.hostinger.yml up -d
    sleep 30
fi

log "Début des corrections..."

# Étape 1: Corriger MongoDB Auth
log "Étape 1/4: Correction de l'authentification MongoDB"
if ./scripts/fix_mongodb_auth.sh; then
    success "MongoDB auth corrigée"
else
    error "Échec de la correction MongoDB"
    exit 1
fi

# Étape 2: Télécharger les modèles Ollama
log "Étape 2/4: Téléchargement des modèles Ollama"
if ./scripts/pull_models_with_retry.sh; then
    success "Modèles Ollama téléchargés"
else
    warning "Téléchargement partiel des modèles"
fi

# Étape 3: Corriger la configuration RAG
log "Étape 3/4: Correction de la configuration RAG"
if ./scripts/fix_rag_config.sh; then
    success "Configuration RAG corrigée"
else
    error "Échec de la correction RAG"
    exit 1
fi

# Étape 4: Redémarrer les services
log "Étape 4/4: Redémarrage des services"
docker-compose -f docker-compose.hostinger.yml restart mcp-api
sleep 30

# Tests de validation
log "Tests de validation..."

# Test 1: Health check
if curl -sf http://localhost:8000/health > /dev/null; then
    success "API Health: OK"
else
    error "API Health: FAILED"
fi

# Test 2: MongoDB connection
if docker exec mcp-mongodb mongosh -u mcpuser -p MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY --authenticationDatabase admin --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    success "MongoDB Auth: OK"
else
    error "MongoDB Auth: FAILED"
fi

# Test 3: Ollama models
MODELS_COUNT=$(docker exec mcp-ollama ollama list | wc -l)
if [ $MODELS_COUNT -gt 1 ]; then
    success "Ollama Models: $((MODELS_COUNT-1)) disponibles"
else
    warning "Ollama Models: Aucun modèle disponible"
fi

# Test 4: RAG endpoint
if curl -sf -X POST http://localhost:8000/api/v1/rag/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer test" \
    -d '{"query": "test", "node_pubkey": "feustey"}' > /dev/null 2>&1; then
    success "RAG Endpoint: OK"
else
    warning "RAG Endpoint: Problème (peut être normal)"
fi

echo ""
echo -e "${GREEN}✅ Corrections terminées !${NC}"
echo ""
echo "Prochaines étapes:"
echo "  1. Vérifier les logs: docker-compose -f docker-compose.hostinger.yml logs -f"
echo "  2. Tester le workflow RAG: ./run_rag_workflow_prod.sh"
echo "  3. Monitorer: python monitor_production.py"
echo ""
