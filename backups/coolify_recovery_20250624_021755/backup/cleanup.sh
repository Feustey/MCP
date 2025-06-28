#!/bin/bash
# Script de nettoyage des sauvegardes MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Variables
BACKUP_DIR="/backups"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Nettoyage des sauvegardes anciennes (rétention: ${RETENTION_DAYS} jours)"

# Suppression des sauvegardes anciennes
if [[ -d "${BACKUP_DIR}" ]]; then
    # Trouver et supprimer les fichiers plus anciens que RETENTION_DAYS
    find "${BACKUP_DIR}" -name "mcp_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -type f | while read -r file; do
        log "Suppression de l'ancienne sauvegarde: $(basename "$file")"
        rm -f "$file"
    done
    
    # Affichage de l'espace utilisé
    TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "0")
    BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "mcp_backup_*.tar.gz" -type f | wc -l)
    
    log "Espace total utilisé par les sauvegardes: ${TOTAL_SIZE}"
    log "Nombre de sauvegardes conservées: ${BACKUP_COUNT}"
else
    log "Répertoire de sauvegarde introuvable: ${BACKUP_DIR}"
fi

log "Nettoyage terminé" 