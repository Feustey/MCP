#!/bin/bash

# Script de déploiement complet MCP en production
# Dernière mise à jour: 7 mai 2025

# Vérification des privilèges root
if [ "$EUID" -ne 0 ]; then
    echo "Ce script doit être exécuté en tant que root"
    echo "Utilisez: sudo $0"
    exit 1
fi

set -e

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${WORKSPACE_DIR}/logs/deploy_${TIMESTAMP}.log"
BACKUP_DIR="${WORKSPACE_DIR}/backups/${TIMESTAMP}"
DATA_ROOT="/opt/mcp/data"

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Fonction de création des répertoires de données
setup_data_directories() {
    log "📁 Création des répertoires de données..."
    
    # Liste des répertoires à créer
    local directories=(
        "${DATA_ROOT}"
        "${DATA_ROOT}/grafana"
        "${DATA_ROOT}/prometheus"
        "${DATA_ROOT}/alertmanager"
        "${DATA_ROOT}/qdrant"
    )
    
    # Création des répertoires avec les bonnes permissions
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chown -R $(logname):$(id -gn $(logname)) "$dir"
        chmod -R 755 "$dir"
    done
    
    log "✅ Répertoires de données créés"
}

# Fonction de sauvegarde
backup() {
    log "📦 Création d'une sauvegarde..."
    
    # Création des répertoires de sauvegarde
    mkdir -p "${WORKSPACE_DIR}/backups"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "${BACKUP_DIR}/volumes"
    
    # Configuration des permissions
    chown -R $(logname):$(id -gn $(logname)) "${WORKSPACE_DIR}/backups"
    chown -R $(logname):$(id -gn $(logname)) "$BACKUP_DIR"
    chown -R $(logname):$(id -gn $(logname)) "${BACKUP_DIR}/volumes"
    
    # Sauvegarde des données
    if [ -d "data" ]; then
        tar -czf "${BACKUP_DIR}/data_backup.tar.gz" data/
    fi
    
    # Sauvegarde des configurations
    if [ -d "config" ]; then
        tar -czf "${BACKUP_DIR}/config_backup.tar.gz" config/
    fi
    
    # Sauvegarde des logs
    if [ -d "logs" ]; then
        tar -czf "${BACKUP_DIR}/logs_backup.tar.gz" logs/
    fi
    
    # Sauvegarde de MongoDB (installé localement)
    if command -v mongodump &> /dev/null; then
        log "📦 Sauvegarde de MongoDB (local)..."
        mkdir -p "${BACKUP_DIR}/mongodb"
        mongodump --out="${BACKUP_DIR}/mongodb" || true
        cd "${BACKUP_DIR}" && tar -czf mongodb_backup.tar.gz mongodb/ && rm -rf mongodb/
    fi
    
    # Sauvegarde de Redis (installé localement)
    if command -v redis-cli &> /dev/null; then
        log "📦 Sauvegarde de Redis (local)..."
        mkdir -p "${BACKUP_DIR}/redis"
        redis-cli --rdb "${BACKUP_DIR}/redis/dump.rdb" || true
        cd "${BACKUP_DIR}" && tar -czf redis_backup.tar.gz redis/ && rm -rf redis/
    fi
    
    # Sauvegarde des volumes Docker
    local volumes=(
        "mcp_grafana_prod_data"
        "mcp_prometheus_prod_data"
        "mcp_alertmanager_prod_data"
        "mcp_qdrant_prod_data"
    )
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            log "📦 Sauvegarde du volume ${volume}..."
            docker run --rm \
                -v "${volume}:/data" \
                -v "${BACKUP_DIR}/volumes:/backup" \
                --user root \
                alpine:latest \
                sh -c "cd /data && tar -czf /backup/${volume}.tar.gz . || true"
        fi
    done
    
    # Ajustement final des permissions
    chown -R $(logname):$(id -gn $(logname)) "$BACKUP_DIR"
    
    log "✅ Sauvegarde terminée dans ${BACKUP_DIR}"
}

# Fonction de vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Vérification des commandes requises
    local required_commands=(
        "docker"
        "docker-compose"
        "python3"
        "certbot"
    )
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log "❌ Commande requise non trouvée: $cmd"
            exit 1
        fi
    done
    
    # Vérification des fichiers requis
    local required_files=(
        "docker-compose.hostinger-local.yml"
        "Dockerfile.api"
        "config/nginx/api.dazno.de.conf"
        "config/backup/backup.sh"
        "config/backup/cleanup.sh"
        ".env"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "❌ Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    # Vérification du service Docker selon l'OS
    case "$(uname -s)" in
        Linux)
            if command -v systemctl >/dev/null 2>&1; then
                if ! systemctl is-active --quiet docker; then
                    log "🔄 Démarrage du service Docker..."
                    systemctl start docker
                fi
            elif command -v service >/dev/null 2>&1; then
                if ! service docker status >/dev/null 2>&1; then
                    log "🔄 Démarrage du service Docker..."
                    service docker start
                fi
            fi
            ;;
        Darwin)
            if ! docker info >/dev/null 2>&1; then
                log "🔄 Démarrage de Docker Desktop..."
                open -a Docker
                # Attente que Docker soit prêt
                for i in {1..30}; do
                    if docker info >/dev/null 2>&1; then
                        break
                    fi
                    sleep 1
                done
            fi
            ;;
        *)
            log "⚠️ Système d'exploitation non reconnu"
            log "📝 Veuillez vérifier que Docker est en cours d'exécution"
            ;;
    esac
    
    # Vérification finale de Docker
    if ! docker info >/dev/null 2>&1; then
        log "❌ Docker n'est pas en cours d'exécution"
        exit 1
    fi
    
    log "✅ Tous les prérequis sont satisfaits"
}

# Fonction de configuration SSL
setup_ssl() {
    log "🔒 Configuration SSL..."
    
    if [ ! -f "/etc/letsencrypt/live/api.dazno.de/fullchain.pem" ]; then
        # Création des répertoires nécessaires
        mkdir -p /etc/letsencrypt
        mkdir -p /var/log/letsencrypt
        
        # Configuration des permissions
        chown -R $(logname):$(id -gn $(logname)) /etc/letsencrypt
        chown -R $(logname):$(id -gn $(logname)) /var/log/letsencrypt
        
        ./scripts/setup_ssl.sh
    else
        log "✅ Certificats SSL déjà présents"
    fi
}

# Fonction de déploiement
deploy() {
    log "🚀 Démarrage du déploiement..."
    
    # Arrêt des services existants
    log "🛑 Arrêt des services existants..."
    docker-compose -f docker-compose.hostinger-local.yml down || true
    
    # Construction des images
    log "🏗️ Construction des images Docker..."
    docker build -t mcp-api:latest -f Dockerfile.api .
    
    # Démarrage des services
    log "▶️ Démarrage des services..."
    docker-compose -f docker-compose.hostinger-local.yml up -d
    
    # Configuration des permissions des volumes
    docker volume ls -q | grep mcp | while read vol; do
        docker run --rm -v "${vol}:/data" alpine chown -R 1000:1000 /data
    done
    
    log "✅ Déploiement terminé"
}

# Fonction de test des endpoints
test_endpoints() {
    log "🔌 Test des endpoints..."
    
    # Attente que l'API soit prête
    sleep 10
    
    if ! python3 scripts/test_endpoints.py; then
        log "❌ Certains endpoints ne répondent pas correctement"
        exit 1
    fi
    
    log "✅ Tous les endpoints sont fonctionnels"
}

# Fonction de configuration du monitoring
setup_monitoring() {
    log "📊 Configuration du monitoring..."
    
    # Vérification des métriques MongoDB
    docker-compose -f docker-compose.hostinger-local.yml exec -T mongodb mongosh --eval "db.serverStatus()"
    
    # Vérification des métriques Redis
    docker-compose -f docker-compose.hostinger-local.yml exec -T redis redis-cli info
    
    # Configuration des alertes Telegram si configurées
    if [ -n "$ALERT_TELEGRAM_BOT_TOKEN" ] && [ -n "$ALERT_TELEGRAM_CHAT_ID" ]; then
        log "🔔 Configuration des alertes Telegram..."
        curl -s -X POST "https://api.telegram.org/bot${ALERT_TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ALERT_TELEGRAM_CHAT_ID}" \
            -d "text=🚀 Déploiement MCP terminé avec succès !"
    fi
    
    log "✅ Monitoring configuré"
}

# Fonction de nettoyage
cleanup() {
    log "🧹 Nettoyage..."
    
    # Suppression des anciennes sauvegardes
    if [ -n "$BACKUP_RETENTION_DAYS" ]; then
        find "${WORKSPACE_DIR}/backups" -type d -mtime +"${BACKUP_RETENTION_DAYS}" -exec rm -rf {} +
    fi
    
    # Suppression des anciennes images Docker
    docker image prune -f
    
    log "✅ Nettoyage terminé"
}

# Fonction principale
main() {
    # Création du répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    chown -R $(logname):$(id -gn $(logname)) "$(dirname "$LOG_FILE")"
    
    log "🎬 Début du déploiement complet MCP"
    
    # Exécution des étapes
    check_prerequisites
    setup_data_directories
    backup
    setup_ssl
    deploy
    test_endpoints
    setup_monitoring
    cleanup
    
    log "🎉 Déploiement complet terminé avec succès!"
    log "📝 Logs disponibles dans: $LOG_FILE"
    log "🌍 API accessible sur: https://api.dazno.de"
}

# Exécution du script
main "$@" 