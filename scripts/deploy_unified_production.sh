#!/bin/bash

# Script de déploiement unifié MCP Production
# Sans Grafana et Prometheus
# Dernière mise à jour: 27 août 2025

set -e
set -o pipefail

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
PROJECT_NAME="mcp-production"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction de log
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
        exit 1
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Fichier .env
    if [ ! -f .env ]; then
        warning ".env n'existe pas. Copie depuis .env.example..."
        if [ -f .env.example ]; then
            cp .env.example .env
        else
            error "Ni .env ni .env.example n'existent"
            exit 1
        fi
    fi
    
    log "✓ Prérequis vérifiés"
}

# Création des répertoires nécessaires
create_directories() {
    log "Création des répertoires..."
    
    # Répertoires MCP
    mkdir -p ./mcp-data/{logs,data,rag,backups,reports}
    
    # Répertoires T4G
    mkdir -p ./t4g-data/{logs,uploads,data}
    
    # Répertoires de configuration
    mkdir -p ./config/{nginx,qdrant,ollama}
    
    # Répertoires de logs
    mkdir -p ./logs/{nginx,mcp,t4g}
    
    # Répertoires de backup
    mkdir -p ./backups
    
    log "✓ Répertoires créés"
}

# Arrêt des anciens containers
stop_old_containers() {
    log "Arrêt des anciens containers..."
    
    # Liste des containers à arrêter
    CONTAINERS=(
        "hostinger-nginx"
        "mcp-api"
        "t4g-api"
        "hostinger-qdrant"
        "hostinger-ollama"
        "hostinger-prometheus"
        "hostinger-grafana"
        "mcp-nginx-production"
        "mcp-api-production"
        "mcp-qdrant-production"
    )
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps -a | grep -q "$container"; then
            log "Arrêt de $container..."
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done
    
    # Arrêt via docker-compose si des fichiers existent
    COMPOSE_FILES=(
        "docker-compose.hostinger-unified.yml"
        "docker-compose.production-complete.yml"
        "docker-compose.monitoring.yml"
    )
    
    for compose in "${COMPOSE_FILES[@]}"; do
        if [ -f "$compose" ]; then
            log "Arrêt des services de $compose..."
            docker-compose -f "$compose" down --remove-orphans 2>/dev/null || true
        fi
    done
    
    log "✓ Anciens containers arrêtés"
}

# Nettoyage Docker
clean_docker() {
    log "Nettoyage Docker..."
    
    # Suppression des containers arrêtés
    docker container prune -f || true
    
    # Suppression des images non utilisées
    docker image prune -f || true
    
    # Suppression des volumes orphelins (sauf ceux avec données)
    docker volume ls -qf dangling=true | grep -v "mcp_" | xargs -r docker volume rm || true
    
    # Suppression des réseaux non utilisés
    docker network prune -f || true
    
    log "✓ Docker nettoyé"
}

# Pull des images
pull_images() {
    log "Récupération des dernières images..."
    
    docker pull nginx:alpine
    docker pull feustey/dazno:latest
    # docker pull feustey/token-for-good:latest  # Pas encore disponible
    docker pull qdrant/qdrant:v1.7.4
    docker pull ollama/ollama:latest
    docker pull alpine:3.18
    
    log "✓ Images récupérées"
}

# Déploiement
deploy() {
    log "Déploiement du nouveau docker-compose unifié..."
    
    # Utilisation de docker compose v2 ou docker-compose v1
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # Démarrage des services
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    
    log "✓ Services déployés"
}

# Vérification santé
health_check() {
    log "Vérification de la santé des services..."
    
    # Attente du démarrage
    sleep 15
    
    # Vérification des containers
    SERVICES=(
        "mcp-nginx-prod"
        "mcp-api-prod"
        # "t4g-api-prod"  # Pas encore déployé
        "mcp-qdrant-prod"
        "mcp-ollama-prod"
    )
    
    ALL_HEALTHY=true
    for service in "${SERVICES[@]}"; do
        if docker ps | grep -q "$service"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$service" 2>/dev/null || echo "not found")
            if [ "$STATUS" = "running" ]; then
                log "✓ $service: Running"
            else
                error "$service: $STATUS"
                ALL_HEALTHY=false
            fi
        else
            error "$service: Not found"
            ALL_HEALTHY=false
        fi
    done
    
    if [ "$ALL_HEALTHY" = true ]; then
        log "✓ Tous les services sont opérationnels"
    else
        error "Certains services ne sont pas opérationnels"
        return 1
    fi
}

# Test des endpoints
test_endpoints() {
    log "Test des endpoints..."
    
    # Attente supplémentaire pour stabilisation
    sleep 10
    
    # Endpoints à tester
    declare -A ENDPOINTS=(
        ["MCP Health"]="http://localhost:8000/api/v1/health"
        # ["T4G Health"]="http://localhost:8001/health"  # Pas encore déployé
        ["Qdrant Health"]="http://localhost:6333/health"
        ["Ollama Version"]="http://localhost:11434/api/version"
        ["Nginx"]="http://localhost/health"
    )
    
    ALL_OK=true
    for name in "${!ENDPOINTS[@]}"; do
        URL="${ENDPOINTS[$name]}"
        
        # Test avec curl
        if curl -f -s -o /dev/null -w "%{http_code}" "$URL" | grep -q "200\|204"; then
            log "✓ $name: OK"
        else
            warning "$name: Non accessible ($URL)"
            ALL_OK=false
        fi
    done
    
    if [ "$ALL_OK" = true ]; then
        log "✓ Tous les endpoints sont fonctionnels"
    else
        warning "Certains endpoints ne sont pas accessibles"
    fi
}

# Affichage des logs
show_logs() {
    log "Logs des dernières 50 lignes de chaque service:"
    
    if docker compose version &> /dev/null; then
        docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50
    else
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail=50
    fi
}

# Fonction principale
main() {
    log "========================================="
    log " Déploiement MCP Production Unifié"
    log " Sans Grafana et Prometheus"
    log "========================================="
    
    check_prerequisites
    create_directories
    stop_old_containers
    clean_docker
    pull_images
    deploy
    
    log "Attente de stabilisation des services (30s)..."
    sleep 30
    
    health_check
    test_endpoints
    
    log "========================================="
    log " Déploiement terminé avec succès!"
    log "========================================="
    log ""
    log "Services disponibles:"
    log " - API MCP: http://localhost:8000"
    log " - API T4G: http://localhost:8001"
    log " - Nginx: http://localhost"
    log ""
    log "Commandes utiles:"
    log " - Voir les logs: docker compose -f $COMPOSE_FILE logs -f"
    log " - Statut: docker compose -f $COMPOSE_FILE ps"
    log " - Arrêter: docker compose -f $COMPOSE_FILE down"
    log ""
    
    # Optionnel: afficher les logs
    read -p "Voulez-vous voir les logs? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
    fi
}

# Gestion des erreurs
trap 'error "Une erreur est survenue. Arrêt du script."; exit 1' ERR

# Lancement
main "$@"