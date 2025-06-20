#!/bin/bash

# Script de déploiement simplifié pour Hostinger
# Dernière mise à jour: 7 janvier 2025

set -e

echo "🚀 Déploiement MCP sur Hostinger - Version Simplifiée"

# Configuration
DOCKER_IMAGE="feustey/dazno"
DOCKER_TAG="latest"
COMPOSE_FILE="docker-compose.hostinger-local.yml"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Vérification des prérequis
log_info "Vérification des prérequis..."

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

log_info "✅ Prérequis vérifiés"

# Création des répertoires nécessaires
log_info "Création des répertoires..."
mkdir -p logs data rag config/mongodb config/prometheus config/grafana/provisioning

# Téléchargement de l'image depuis Docker Hub
log_info "Téléchargement de l'image Docker depuis Docker Hub..."
docker pull ${DOCKER_IMAGE}:${DOCKER_TAG}

if [ $? -ne 0 ]; then
    log_error "❌ Échec du téléchargement de l'image Docker"
    exit 1
fi

log_info "✅ Image téléchargée avec succès"

# Arrêt des conteneurs existants
log_info "Arrêt des conteneurs existants..."
docker-compose -f ${COMPOSE_FILE} down --remove-orphans || true

# Nettoyage des volumes orphelins (optionnel)
log_warn "Nettoyage des volumes orphelins..."
docker volume prune -f || true

# Démarrage des services
log_info "Démarrage des services..."
docker-compose -f ${COMPOSE_FILE} up -d

# Attendre que les services soient prêts
log_info "Attente du démarrage des services..."
sleep 45

# Vérification de la santé des services
log_info "Vérification de la santé des services..."

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
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_info "✅ API MCP: Opérationnel"
else
    log_warn "⚠️ API MCP: Problème de santé (peut être normal au premier démarrage)"
fi

# Caddy
if curl -f http://localhost:80 > /dev/null 2>&1; then
    log_info "✅ Caddy: Opérationnel"
else
    log_warn "⚠️ Caddy: Problème de santé (peut être normal au premier démarrage)"
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
echo ""

# Vérification finale
log_info "Test de connectivité finale..."
if curl -f http://api.dazno.de/health > /dev/null 2>&1; then
    log_info "✅ Déploiement réussi - API accessible"
else
    log_warn "⚠️ API non accessible immédiatement"
    log_info "💡 Vérifiez les logs avec: docker-compose -f ${COMPOSE_FILE} logs -f"
    log_info "💡 L'API peut prendre quelques minutes à démarrer complètement"
fi

echo ""
log_info "🚀 Déploiement terminé! Vérifiez les logs si nécessaire." 