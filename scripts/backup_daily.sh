#!/bin/bash

################################################################################
# Script de Backup Quotidien MCP
#
# Sauvegarde:
# - Qdrant vector database
# - Données applicatives (mcp-data)
# - Configuration (.env.production)
# - Logs
#
# Usage:
#   ./scripts/backup_daily.sh
#
# Cron: 0 3 * * * /opt/mcp/scripts/backup_daily.sh
#
# Auteur: MCP Team
# Date: 16 octobre 2025
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/opt/mcp"
BACKUP_DIR="$PROJECT_DIR/backups"
RETENTION_DAYS=30

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Banner
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          MCP - Backup Quotidien                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# 1. Backup MongoDB Local
log_info "1/6 - Backup MongoDB Local"
if docker ps | grep -q "mcp-mongodb-prod"; then
    # Create backup inside container
    if docker exec mcp-mongodb-prod mongodump \
        --username=mcp_admin \
        --password=mcp_secure_password_2025 \
        --authenticationDatabase=admin \
        --db=mcp_prod \
        --out="/backup/mongodb_$DATE" 2>/dev/null; then
        
        # Compress inside container
        docker exec mcp-mongodb-prod tar czf \
            "/backup/mongodb_${DATE}.tar.gz" \
            -C /backup "mongodb_$DATE" 2>/dev/null
        
        # Copy to host
        docker cp "mcp-mongodb-prod:/backup/mongodb_${DATE}.tar.gz" \
            "$BACKUP_DIR/" 2>/dev/null
        
        # Cleanup container backup
        docker exec mcp-mongodb-prod rm -rf "/backup/mongodb_$DATE" 2>/dev/null
        
        SIZE=$(du -h "$BACKUP_DIR/mongodb_${DATE}.tar.gz" 2>/dev/null | cut -f1)
        log_success "MongoDB sauvegardé ($SIZE)"
    else
        log_error "Échec backup MongoDB"
    fi
else
    log_error "Conteneur MongoDB non trouvé"
fi
echo ""

# 2. Backup Redis Local
log_info "2/6 - Backup Redis Local"
if docker ps | grep -q "mcp-redis-prod"; then
    # Trigger Redis save
    docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 BGSAVE 2>/dev/null
    sleep 5
    
    # Backup Redis data volume
    if docker run --rm \
        -v mcp_redis_data:/data \
        -v "$BACKUP_DIR":/backup \
        alpine \
        tar czf "/backup/redis_$DATE.tar.gz" -C /data . 2>/dev/null; then
        
        SIZE=$(du -h "$BACKUP_DIR/redis_$DATE.tar.gz" | cut -f1)
        log_success "Redis sauvegardé ($SIZE)"
    else
        log_error "Échec backup Redis"
    fi
else
    log_error "Conteneur Redis non trouvé"
fi
echo ""

# 3. Backup Qdrant Vector Database
log_info "3/6 - Backup Qdrant Vector Database"
if docker ps | grep -q "mcp-qdrant-prod"; then
    if docker run --rm \
        -v mcp_qdrant_data:/data \
        -v "$BACKUP_DIR":/backup \
        alpine \
        tar czf "/backup/qdrant_$DATE.tar.gz" -C /data . 2>/dev/null; then
        
        SIZE=$(du -h "$BACKUP_DIR/qdrant_$DATE.tar.gz" | cut -f1)
        log_success "Qdrant sauvegardé ($SIZE)"
    else
        log_error "Échec backup Qdrant"
    fi
else
    log_error "Conteneur Qdrant non trouvé"
fi
echo ""

# 4. Backup Ollama Models (optionnel - volumineux)
log_info "4/6 - Backup Ollama Models (skip - trop volumineux)"
# Optionnel: Décommenter pour sauvegarder Ollama
# if docker ps | grep -q "mcp-ollama"; then
#     docker run --rm \
#         -v mcp_ollama_data:/data \
#         -v "$BACKUP_DIR":/backup \
#         alpine \
#         tar czf "/backup/ollama_$DATE.tar.gz" -C /data .
#     log_success "Ollama sauvegardé"
# fi
log_info "Ollama models non sauvegardés (téléchargeables)"
echo ""

# 5. Backup Application Data
log_info "5/6 - Backup Application Data"
if [ -d "$PROJECT_DIR/mcp-data" ]; then
    tar czf "$BACKUP_DIR/mcp_data_$DATE.tar.gz" \
        -C "$PROJECT_DIR" \
        mcp-data 2>/dev/null
    
    SIZE=$(du -h "$BACKUP_DIR/mcp_data_$DATE.tar.gz" | cut -f1)
    log_success "Données applicatives sauvegardées ($SIZE)"
else
    log_error "Répertoire mcp-data non trouvé"
fi
echo ""

# 6. Backup Configuration
log_info "6/6 - Backup Configuration"
if [ -f "$PROJECT_DIR/.env.production" ]; then
    # Backup .env (sensible - permissions restrictives)
    cp "$PROJECT_DIR/.env.production" "$BACKUP_DIR/env_production_$DATE.backup"
    chmod 600 "$BACKUP_DIR/env_production_$DATE.backup"
    log_success "Configuration sauvegardée"
    
    # Backup aussi le docker-compose
    if [ -f "$PROJECT_DIR/docker-compose.production.yml" ]; then
        cp "$PROJECT_DIR/docker-compose.production.yml" "$BACKUP_DIR/docker_compose_$DATE.yml"
        log_success "Docker Compose sauvegardé"
    fi
else
    log_error ".env.production non trouvé"
fi
echo ""

# 7. Cleanup Old Backups
log_info "7/7 - Nettoyage des anciens backups (> $RETENTION_DAYS jours)"
CLEANED=0

# MongoDB backups
CLEANED_MONGODB=$(find "$BACKUP_DIR" -name "mongodb_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_MONGODB))

# Redis backups
CLEANED_REDIS=$(find "$BACKUP_DIR" -name "redis_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_REDIS))

# Qdrant backups
CLEANED_QDRANT=$(find "$BACKUP_DIR" -name "qdrant_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_QDRANT))

# Data backups
CLEANED_DATA=$(find "$BACKUP_DIR" -name "mcp_data_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_DATA))

# Config backups
CLEANED_ENV=$(find "$BACKUP_DIR" -name "env_production_*.backup" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_ENV))

# Docker compose backups
CLEANED_DOCKER=$(find "$BACKUP_DIR" -name "docker_compose_*.yml" -mtime +$RETENTION_DAYS -delete -print | wc -l)
CLEANED=$((CLEANED + CLEANED_DOCKER))

if [ "$CLEANED" -gt 0 ]; then
    log_success "$CLEANED ancien(s) backup(s) supprimé(s)"
else
    log_info "Aucun ancien backup à supprimer"
fi
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              Backup Terminé                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Backups créés dans: $BACKUP_DIR"
echo ""

# List recent backups
log_info "Backups récents:"
ls -lh "$BACKUP_DIR" | tail -10
echo ""

# Disk usage
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log_info "Taille totale des backups: $BACKUP_SIZE"

# Disk space available
DISK_FREE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $4}')
log_info "Espace disque disponible: $DISK_FREE"

echo ""
log_success "✓ Backup quotidien terminé avec succès"
echo ""

# Send notification via Telegram (if configured)
if [ -f "$PROJECT_DIR/.env.production" ]; then
    source "$PROJECT_DIR/.env.production"
    
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        MESSAGE="✅ MCP Backup terminé
Date: $(date '+%Y-%m-%d %H:%M:%S')
Taille: $BACKUP_SIZE
Espace libre: $DISK_FREE"
        
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=$MESSAGE" \
            > /dev/null 2>&1 || true
    fi
fi

exit 0

