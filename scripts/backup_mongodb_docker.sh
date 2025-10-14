#!/bin/bash

################################################################################
# Script de Backup MongoDB (Docker)
#
# Crée un backup complet de MongoDB depuis le container Docker
# Compression automatique et rétention des 7 derniers jours
#
# Usage: ./scripts/backup_mongodb_docker.sh
#
# Auteur: MCP Team
# Date: 13 octobre 2025
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="/home/feustey/mcp-production/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="mcp-mongodb"

# Lire depuis .env
if [ -f .env ]; then
    source .env
fi

MONGODB_USER="${MONGODB_USER:-mcpuser}"
MONGODB_PASS="${MONGODB_PASSWORD:-ChangeThisPassword123!}"
MONGODB_DB="${MONGODB_DATABASE:-mcp_prod}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier que le container existe
check_container() {
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container ${CONTAINER_NAME} introuvable"
        exit 1
    fi
    
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container ${CONTAINER_NAME} n'est pas en cours d'exécution"
        exit 1
    fi
}

# Créer le répertoire de backup
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_info "Répertoire de backup: $BACKUP_DIR"
}

# Effectuer le backup
perform_backup() {
    log_info "Démarrage du backup MongoDB..."
    
    # Backup dans le container
    docker exec "$CONTAINER_NAME" mongodump \
        --username="$MONGODB_USER" \
        --password="$MONGODB_PASS" \
        --authenticationDatabase=admin \
        --db="$MONGODB_DB" \
        --out="/data/backup_$DATE" \
        --gzip
    
    if [ $? -eq 0 ]; then
        log_success "Dump MongoDB créé avec succès"
    else
        log_error "Échec du dump MongoDB"
        exit 1
    fi
}

# Copier le backup hors du container
copy_backup() {
    log_info "Copie du backup hors du container..."
    
    docker cp "$CONTAINER_NAME:/data/backup_$DATE" "$BACKUP_DIR/"
    
    if [ $? -eq 0 ]; then
        log_success "Backup copié vers $BACKUP_DIR/backup_$DATE"
    else
        log_error "Échec de la copie du backup"
        exit 1
    fi
}

# Compresser le backup
compress_backup() {
    log_info "Compression du backup..."
    
    cd "$BACKUP_DIR"
    tar -czf "mongodb_${MONGODB_DB}_${DATE}.tar.gz" "backup_$DATE"
    
    if [ $? -eq 0 ]; then
        # Supprimer le répertoire non compressé
        rm -rf "backup_$DATE"
        
        # Nettoyer dans le container
        docker exec "$CONTAINER_NAME" rm -rf "/data/backup_$DATE"
        
        BACKUP_SIZE=$(du -h "mongodb_${MONGODB_DB}_${DATE}.tar.gz" | cut -f1)
        log_success "Backup compressé: mongodb_${MONGODB_DB}_${DATE}.tar.gz ($BACKUP_SIZE)"
    else
        log_error "Échec de la compression"
        exit 1
    fi
}

# Nettoyer les anciens backups (garder 7 jours)
cleanup_old_backups() {
    log_info "Nettoyage des anciens backups (> 7 jours)..."
    
    cd "$BACKUP_DIR"
    find . -name "mongodb_*.tar.gz" -mtime +7 -delete
    
    REMAINING=$(ls -1 mongodb_*.tar.gz 2>/dev/null | wc -l)
    log_success "Backups restants: $REMAINING"
}

# Afficher les statistiques
show_stats() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              Backup MongoDB - Résumé                       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Date:        $(date)"
    echo "Base:        $MONGODB_DB"
    echo "Container:   $CONTAINER_NAME"
    echo "Backup:      mongodb_${MONGODB_DB}_${DATE}.tar.gz"
    echo ""
    
    cd "$BACKUP_DIR"
    echo "Liste des backups disponibles:"
    ls -lh mongodb_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    echo "Taille totale: $TOTAL_SIZE"
    echo ""
}

# Main execution
main() {
    log_info "╔════════════════════════════════════════════════╗"
    log_info "║   Backup MongoDB Docker - MCP v1.0            ║"
    log_info "╚════════════════════════════════════════════════╝"
    echo ""
    
    check_container
    create_backup_dir
    perform_backup
    copy_backup
    compress_backup
    cleanup_old_backups
    show_stats
    
    log_success "✅ Backup terminé avec succès !"
}

# Run
main "$@"

