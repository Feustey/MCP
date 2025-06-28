#!/bin/bash
# Script de sauvegarde MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${WORKSPACE_DIR}/backups/${TIMESTAMP}"
LOG_FILE="${WORKSPACE_DIR}/logs/backup_${TIMESTAMP}.log"

# Chargement des variables d'environnement
if [ -f "${WORKSPACE_DIR}/.env" ]; then
    source "${WORKSPACE_DIR}/.env"
fi

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Fonction de sauvegarde locale
backup_local() {
    log "📦 Création d'une sauvegarde locale..."
    
    # Création du répertoire de sauvegarde
    mkdir -p "$BACKUP_DIR"
    
    # Sauvegarde des données
    if [ -d "${WORKSPACE_DIR}/data" ]; then
        tar -czf "${BACKUP_DIR}/data_backup.tar.gz" -C "${WORKSPACE_DIR}" data/
    fi
    
    # Sauvegarde des configurations
    if [ -d "${WORKSPACE_DIR}/config" ]; then
        tar -czf "${BACKUP_DIR}/config_backup.tar.gz" -C "${WORKSPACE_DIR}" config/
    fi
    
    # Sauvegarde des logs
    if [ -d "${WORKSPACE_DIR}/logs" ]; then
        tar -czf "${BACKUP_DIR}/logs_backup.tar.gz" -C "${WORKSPACE_DIR}" logs/
    fi
    
    # Sauvegarde des volumes Docker
    if docker volume ls | grep -q mcp; then
        mkdir -p "${BACKUP_DIR}/volumes"
        
        # MongoDB
        log "💾 Sauvegarde de MongoDB..."
        docker-compose -f "${WORKSPACE_DIR}/docker-compose.hostinger-local.yml" exec -T mongodb mongodump --archive > "${BACKUP_DIR}/volumes/mongodb_dump.archive"
        
        # Redis
        log "💾 Sauvegarde de Redis..."
        docker-compose -f "${WORKSPACE_DIR}/docker-compose.hostinger-local.yml" exec -T redis redis-cli SAVE
        docker run --rm -v mcp-redis:/data -v "${BACKUP_DIR}/volumes":/backup alpine tar -czf /backup/redis_data.tar.gz /data
    fi
    
    log "✅ Sauvegarde locale terminée dans ${BACKUP_DIR}"
}

# Fonction de sauvegarde S3 (si configuré)
backup_s3() {
    if [ -n "$BACKUP_S3_BUCKET" ] && [ -n "$BACKUP_S3_ACCESS_KEY" ] && [ -n "$BACKUP_S3_SECRET_KEY" ]; then
        log "☁️ Envoi de la sauvegarde vers S3..."
        
        # Installation de AWS CLI si nécessaire
        if ! command -v aws >/dev/null 2>&1; then
            log "📦 Installation de AWS CLI..."
            pip install awscli
        fi
        
        # Configuration des credentials AWS
        export AWS_ACCESS_KEY_ID="$BACKUP_S3_ACCESS_KEY"
        export AWS_SECRET_ACCESS_KEY="$BACKUP_S3_SECRET_KEY"
        
        # Envoi des fichiers vers S3
        aws s3 sync "$BACKUP_DIR" "s3://${BACKUP_S3_BUCKET}/${TIMESTAMP}/"
        
        log "✅ Sauvegarde S3 terminée"
    else
        log "ℹ️ Sauvegarde S3 non configurée"
    fi
}

# Fonction de nettoyage
cleanup() {
    log "🧹 Nettoyage des anciennes sauvegardes..."
    
    # Suppression des anciennes sauvegardes locales
    if [ -n "$BACKUP_RETENTION_DAYS" ]; then
        find "${WORKSPACE_DIR}/backups" -type d -mtime +"${BACKUP_RETENTION_DAYS}" -exec rm -rf {} +
    fi
    
    # Suppression des anciennes sauvegardes S3
    if [ -n "$BACKUP_S3_BUCKET" ] && [ -n "$BACKUP_RETENTION_DAYS" ]; then
        # Calcul de la date limite
        LIMIT_DATE=$(date -v-"${BACKUP_RETENTION_DAYS}"d +%Y%m%d)
        
        # Liste et suppression des anciennes sauvegardes
        aws s3 ls "s3://${BACKUP_S3_BUCKET}/" | while read -r line; do
            backup_date=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1 | cut -d'_' -f1)
            if [ "$backup_date" \< "$LIMIT_DATE" ]; then
                aws s3 rm --recursive "s3://${BACKUP_S3_BUCKET}/${line##* }"
            fi
        done
    fi
    
    log "✅ Nettoyage terminé"
}

# Fonction principale
main() {
    # Création du répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "🎬 Début de la sauvegarde MCP"
    
    # Exécution des étapes
    backup_local
    backup_s3
    cleanup
    
    log "🎉 Sauvegarde terminée avec succès!"
    log "📝 Logs disponibles dans: $LOG_FILE"
}

# Exécution du script
main "$@" 