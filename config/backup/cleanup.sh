#!/bin/bash
# Script de nettoyage des sauvegardes MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Configuration
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_FILE="${WORKSPACE_DIR}/logs/cleanup_$(date +%Y%m%d_%H%M%S).log"

# Chargement des variables d'environnement
if [ -f "${WORKSPACE_DIR}/.env" ]; then
    source "${WORKSPACE_DIR}/.env"
fi

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Fonction de nettoyage local
cleanup_local() {
    log "🧹 Nettoyage des sauvegardes locales..."
    
    if [ -n "$BACKUP_RETENTION_DAYS" ]; then
        # Suppression des anciennes sauvegardes
        find "${WORKSPACE_DIR}/backups" -type d -mtime +"${BACKUP_RETENTION_DAYS}" -exec rm -rf {} +
        
        # Suppression des anciens logs
        find "${WORKSPACE_DIR}/logs" -type f -name "*.log" -mtime +"${BACKUP_RETENTION_DAYS}" -exec rm -f {} +
        
        log "✅ Nettoyage local terminé"
    else
        log "⚠️ BACKUP_RETENTION_DAYS non défini, aucun nettoyage effectué"
    fi
}

# Fonction de nettoyage S3
cleanup_s3() {
    if [ -n "$BACKUP_S3_BUCKET" ] && [ -n "$BACKUP_RETENTION_DAYS" ]; then
        log "☁️ Nettoyage des sauvegardes S3..."
        
        # Vérification de AWS CLI
        if ! command -v aws >/dev/null 2>&1; then
            log "📦 Installation de AWS CLI..."
            pip install awscli
        fi
        
        # Configuration des credentials AWS
        if [ -n "$BACKUP_S3_ACCESS_KEY" ] && [ -n "$BACKUP_S3_SECRET_KEY" ]; then
            export AWS_ACCESS_KEY_ID="$BACKUP_S3_ACCESS_KEY"
            export AWS_SECRET_ACCESS_KEY="$BACKUP_S3_SECRET_KEY"
            
            # Calcul de la date limite
            LIMIT_DATE=$(date -v-"${BACKUP_RETENTION_DAYS}"d +%Y%m%d)
            
            # Liste et suppression des anciennes sauvegardes
            aws s3 ls "s3://${BACKUP_S3_BUCKET}/" | while read -r line; do
                backup_date=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1 | cut -d'_' -f1)
                if [ "$backup_date" \< "$LIMIT_DATE" ]; then
                    backup_path="${line##* }"
                    log "🗑️ Suppression de s3://${BACKUP_S3_BUCKET}/${backup_path}"
                    aws s3 rm --recursive "s3://${BACKUP_S3_BUCKET}/${backup_path}"
                fi
            done
            
            log "✅ Nettoyage S3 terminé"
        else
            log "⚠️ Credentials AWS manquants"
        fi
    else
        log "ℹ️ Nettoyage S3 non configuré"
    fi
}

# Fonction de nettoyage Docker
cleanup_docker() {
    log "🐳 Nettoyage Docker..."
    
    # Suppression des conteneurs arrêtés
    if docker ps -aq --filter status=exited --filter status=created | grep -q .; then
        docker rm $(docker ps -aq --filter status=exited --filter status=created)
        log "✅ Conteneurs arrêtés supprimés"
    else
        log "ℹ️ Aucun conteneur à supprimer"
    fi
    
    # Suppression des images non utilisées
    if docker images -f "dangling=true" -q | grep -q .; then
        docker rmi $(docker images -f "dangling=true" -q)
        log "✅ Images non utilisées supprimées"
    else
        log "ℹ️ Aucune image à supprimer"
    fi
    
    # Nettoyage des volumes non utilisés
    if docker volume ls -qf dangling=true | grep -q .; then
        docker volume rm $(docker volume ls -qf dangling=true)
        log "✅ Volumes non utilisés supprimés"
    else
        log "ℹ️ Aucun volume à supprimer"
    fi
    
    log "✅ Nettoyage Docker terminé"
}

# Fonction principale
main() {
    # Création du répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "🎬 Début du nettoyage MCP"
    
    # Exécution des étapes
    cleanup_local
    cleanup_s3
    cleanup_docker
    
    log "🎉 Nettoyage terminé avec succès!"
    log "📝 Logs disponibles dans: $LOG_FILE"
}

# Exécution du script
main "$@" 