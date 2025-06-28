#!/bin/bash

# Script de déploiement pour développement local sur macOS
# Dernière mise à jour: 28 juin 2025

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

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Fonction de sauvegarde
backup() {
    log "📦 Création d'une sauvegarde..."
    
    # Création des répertoires de sauvegarde
    mkdir -p "${WORKSPACE_DIR}/backups"
    mkdir -p "$BACKUP_DIR"
    
    # Configuration des permissions
    chown -R $(logname):$(id -gn $(logname)) "${WORKSPACE_DIR}/backups"
    chown -R $(logname):$(id -gn $(logname)) "$BACKUP_DIR"
    
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
    )
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log "❌ Commande requise non trouvée: $cmd"
            exit 1
        fi
    done
    
    # Vérification des fichiers requis
    local required_files=(
        "docker-compose.macos.yml"
        "Dockerfile.api"
        ".env"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "❌ Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    # Vérification de Docker Desktop
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
    
    # Vérification finale de Docker
    if ! docker info >/dev/null 2>&1; then
        log "❌ Docker n'est pas en cours d'exécution"
        exit 1
    fi
    
    log "✅ Tous les prérequis sont satisfaits"
}

# Fonction de déploiement
deploy() {
    log "🚀 Démarrage du déploiement..."
    
    # Arrêt des services existants
    log "🛑 Arrêt des services existants..."
    docker-compose -f docker-compose.macos.yml down || true
    
    # Construction des images
    log "🏗️ Construction des images Docker..."
    docker build -t mcp-api:latest -f Dockerfile.api .
    
    # Démarrage des services
    log "▶️ Démarrage des services..."
    docker-compose -f docker-compose.macos.yml up -d
    
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
    
    log "🎬 Début du déploiement local sur macOS"
    
    # Exécution des étapes
    check_prerequisites
    backup
    deploy
    test_endpoints
    cleanup
    
    log "✅ Déploiement terminé avec succès"
}

# Exécution du script
main "$@" 