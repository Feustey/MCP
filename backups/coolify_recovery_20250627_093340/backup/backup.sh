#!/bin/bash
# Script de sauvegarde MCP Production
# Dernière mise à jour: 7 mai 2025

set -e

# Variables
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="mcp_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Fonction de notification Telegram
send_telegram() {
    local message="$1"
    local status="$2"
    
    if [[ -n "${TELEGRAM_BOT_TOKEN}" && -n "${TELEGRAM_CHAT_ID}" ]]; then
        local emoji="✅"
        [[ "$status" == "error" ]] && emoji="❌"
        
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${emoji} **MCP Backup** ${message}" \
            -d parse_mode="Markdown" || true
    fi
}

# Fonction de log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Début de la sauvegarde MCP"
send_telegram "Début de la sauvegarde automatique" "info"

# Création du répertoire de sauvegarde
mkdir -p "${BACKUP_PATH}"

# Sauvegarde MongoDB
log "Sauvegarde de MongoDB..."
if mongodump --host mongodb:27017 \
    --username "${MONGO_ROOT_USER}" \
    --password "${MONGO_ROOT_PASSWORD}" \
    --authenticationDatabase admin \
    --db mcp_prod \
    --out "${BACKUP_PATH}/mongodb"; then
    log "Sauvegarde MongoDB réussie"
else
    log "Erreur lors de la sauvegarde MongoDB"
    send_telegram "Erreur lors de la sauvegarde MongoDB" "error"
    exit 1
fi

# Sauvegarde Redis
log "Sauvegarde de Redis..."
if redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --rdb "${BACKUP_PATH}/redis_dump.rdb"; then
    log "Sauvegarde Redis réussie"
else
    log "Erreur lors de la sauvegarde Redis"
    send_telegram "Erreur lors de la sauvegarde Redis" "error"
    exit 1
fi

# Sauvegarde des logs d'application
log "Sauvegarde des logs..."
if [[ -d "/app-logs" ]]; then
    cp -r /app-logs "${BACKUP_PATH}/logs" 2>/dev/null || true
    log "Sauvegarde des logs réussie"
fi

# Sauvegarde des données Grafana
log "Sauvegarde de Grafana..."
if [[ -d "/grafana-data" ]]; then
    tar -czf "${BACKUP_PATH}/grafana_data.tar.gz" -C /grafana-data . 2>/dev/null || true
    log "Sauvegarde Grafana réussie"
fi

# Sauvegarde des données Qdrant
log "Sauvegarde de Qdrant..."
if [[ -d "/qdrant-data" ]]; then
    tar -czf "${BACKUP_PATH}/qdrant_data.tar.gz" -C /qdrant-data . 2>/dev/null || true
    log "Sauvegarde Qdrant réussie"
fi

# Création de l'archive finale
log "Création de l'archive finale..."
cd "${BACKUP_DIR}"
if tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"; then
    rm -rf "${BACKUP_PATH}"
    log "Archive créée: ${BACKUP_NAME}.tar.gz"
    
    # Calcul de la taille
    SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    log "Taille de la sauvegarde: ${SIZE}"
    
    send_telegram "Sauvegarde terminée avec succès (${SIZE})" "success"
else
    log "Erreur lors de la création de l'archive"
    send_telegram "Erreur lors de la création de l'archive" "error"
    exit 1
fi

# Nettoyage des anciennes sauvegardes
log "Nettoyage des anciennes sauvegardes..."
/usr/local/bin/cleanup.sh

log "Sauvegarde terminée avec succès" 