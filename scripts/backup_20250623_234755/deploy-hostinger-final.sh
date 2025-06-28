#!/bin/bash

# Script de déploiement final pour Hostinger
# Dernière mise à jour: 7 janvier 2025

set -e

echo "🚀 Déploiement MCP sur Hostinger - Version Finale"

# Configuration
DOCKER_IMAGE="feustey/dazno"
DOCKER_TAG="latest"
COMPOSE_FILE="docker-compose.hostinger-local.yml"
PROJECT_NAME="mcp"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Fonction de vérification de santé
check_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Vérification de la santé de $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_info "✅ $service: Opérationnel"
            return 0
        else
            log_warn "⏳ $service: Tentative $attempt/$max_attempts..."
            sleep 10
            ((attempt++))
        fi
    done
    
    log_error "❌ $service: Échec après $max_attempts tentatives"
    return 1
}

# Vérification des prérequis
log_step "Vérification des prérequis..."

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé"
    exit 1
fi

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose n'est pas installé"
    exit 1
fi

# Vérifier que Docker est en cours d'exécution
if ! docker info > /dev/null 2>&1; then
    log_error "Docker n'est pas en cours d'exécution"
    exit 1
fi

log_info "✅ Prérequis vérifiés"

# Création des répertoires nécessaires
log_step "Création des répertoires..."
mkdir -p logs data rag config/mongodb config/prometheus config/grafana/provisioning
log_info "✅ Répertoires créés"

# Sauvegarde de l'ancienne configuration (si elle existe)
if [ -f "$COMPOSE_FILE" ]; then
    log_info "Sauvegarde de l'ancienne configuration..."
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Téléchargement de l'image depuis Docker Hub
log_step "Téléchargement de l'image Docker depuis Docker Hub..."
docker pull ${DOCKER_IMAGE}:${DOCKER_TAG}

if [ $? -ne 0 ]; then
    log_error "❌ Échec du téléchargement de l'image Docker"
    exit 1
fi

log_info "✅ Image téléchargée avec succès"

# Arrêt des conteneurs existants
log_step "Arrêt des conteneurs existants..."
docker-compose -f ${COMPOSE_FILE} down --remove-orphans || true
log_info "✅ Conteneurs arrêtés"

# Nettoyage des ressources
log_step "Nettoyage des ressources..."
docker system prune -f || true
docker volume prune -f || true
log_info "✅ Nettoyage terminé"

# Démarrage des services
log_step "Démarrage des services..."
docker-compose -f ${COMPOSE_FILE} up -d

if [ $? -ne 0 ]; then
    log_error "❌ Échec du démarrage des services"
    docker-compose -f ${COMPOSE_FILE} logs
    exit 1
fi

log_info "✅ Services démarrés"

# Attendre que les services soient prêts
log_step "Attente du démarrage des services..."
sleep 30

# Vérification de la santé des services
log_step "Vérification de la santé des services..."

# MongoDB
if docker-compose -f ${COMPOSE_FILE} exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    log_info "✅ MongoDB: Opérationnel"
else
    log_warn "⚠️ MongoDB: Problème de santé (peut être normal au premier démarrage)"
fi

# Redis
if docker-compose -f ${COMPOSE_FILE} exec -T redis redis-cli ping > /dev/null 2>&1; then
    log_info "✅ Redis: Opérationnel"
else
    log_warn "⚠️ Redis: Problème de santé (peut être normal au premier démarrage)"
fi

# API MCP
check_health "API MCP" "http://localhost:8000/health"

# Caddy
check_health "Caddy" "http://localhost:80"

# Vérification des logs
log_step "Vérification des logs..."
if docker-compose -f ${COMPOSE_FILE} logs --tail=50 | grep -i "error\|exception\|traceback" > /dev/null; then
    log_warn "⚠️ Erreurs détectées dans les logs"
    docker-compose -f ${COMPOSE_FILE} logs --tail=20
else
    log_info "✅ Aucune erreur critique détectée dans les logs"
fi

# Test de connectivité externe
log_step "Test de connectivité externe..."
if curl -f -s "http://api.dazno.de/health" > /dev/null 2>&1; then
    log_info "✅ API accessible via le domaine"
else
    log_warn "⚠️ API non accessible via le domaine (peut être normal si DNS pas encore propagé)"
fi

# Affichage des informations de déploiement
log_info "🎉 Déploiement terminé!"
echo ""
echo "🌐 Informations de déploiement:"
echo "   🌐 API: http://api.dazno.de"
echo "   📊 Documentation: http://api.dazno.de/docs"
echo "   🔍 Health Check: http://api.dazno.de/health"
echo "   📈 Grafana: http://localhost:3000 (admin/admin123)"
echo "   📊 Prometheus: http://localhost:9090"
echo ""
echo "🔧 Commandes utiles:"
echo "   Voir les logs: docker-compose -f ${COMPOSE_FILE} logs -f"
echo "   Redémarrer: docker-compose -f ${COMPOSE_FILE} restart"
echo "   Arrêter: docker-compose -f ${COMPOSE_FILE} down"
echo "   Voir les logs d'un service: docker-compose -f ${COMPOSE_FILE} logs -f mcp-api"
echo "   Vérifier les conteneurs: docker ps"
echo "   Vérifier les volumes: docker volume ls"
echo ""

# Vérification finale
log_step "Vérification finale..."
if docker ps | grep -q "mcp-api"; then
    log_info "✅ Conteneur MCP API en cours d'exécution"
else
    log_error "❌ Conteneur MCP API non trouvé"
fi

if docker ps | grep -q "mongodb"; then
    log_info "✅ Conteneur MongoDB en cours d'exécution"
else
    log_error "❌ Conteneur MongoDB non trouvé"
fi

if docker ps | grep -q "redis"; then
    log_info "✅ Conteneur Redis en cours d'exécution"
else
    log_error "❌ Conteneur Redis non trouvé"
fi

if docker ps | grep -q "caddy"; then
    log_info "✅ Conteneur Caddy en cours d'exécution"
else
    log_error "❌ Conteneur Caddy non trouvé"
fi

echo ""
log_info "🚀 Déploiement terminé avec succès!"
log_info "💡 Vérifiez les logs si nécessaire avec: docker-compose -f ${COMPOSE_FILE} logs -f" 