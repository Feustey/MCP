#!/bin/bash

# Script de déploiement complet MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}"
LOG_FILE="${WORKSPACE_DIR}/logs/deploy_${TIMESTAMP}.log"

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Fonction de sauvegarde
backup() {
    log "📦 Création d'une sauvegarde..."
    mkdir -p "$BACKUP_DIR"
    
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
    
    log "✅ Sauvegarde terminée dans ${BACKUP_DIR}"
}

# Fonction de vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Vérification de Docker
    if ! command -v docker >/dev/null 2>&1; then
        log "❌ Docker n'est pas installé"
        exit 1
    fi
    
    # Vérification de Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        log "❌ Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Vérification de Python
    if ! command -v python3 >/dev/null 2>&1; then
        log "❌ Python 3 n'est pas installé"
        exit 1
    fi
    
    # Vérification des fichiers requis
    required_files=(
        "docker-compose.hostinger-local.yml"
        "Dockerfile.api"
        "config/nginx/api.dazno.de.conf"
        "config/backup/backup.sh"
        "config/backup/cleanup.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log "❌ Fichier requis manquant: $file"
            exit 1
        fi
    done
    
    log "✅ Tous les prérequis sont satisfaits"
}

# Fonction de vérification de la sécurité
check_security() {
    log "🔒 Vérification de la sécurité..."
    
    if ! python3 scripts/check_security.py; then
        log "❌ Des problèmes de sécurité ont été détectés"
        exit 1
    fi
    
    log "✅ Vérification de sécurité réussie"
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
    
    log "✅ Monitoring configuré"
}

# Fonction principale
main() {
    # Création du répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "🎬 Début du déploiement complet MCP"
    
    # Exécution des étapes
    check_prerequisites
    backup
    check_security
    deploy
    test_endpoints
    setup_monitoring
    
    log "🎉 Déploiement complet terminé avec succès!"
    log "📝 Logs disponibles dans: $LOG_FILE"
    log "🌍 API accessible sur: http://localhost/"
}

# Exécution du script
main "$@" 