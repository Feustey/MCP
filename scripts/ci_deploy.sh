#!/bin/bash
################################################################################
# Script de déploiement CI/CD pour Hostinger
# Appelé par GitHub Actions pour automatiser le déploiement
#
# Usage: ./ci_deploy.sh
#
# Variables d'environnement requises:
#   - DEPLOY_DIR: Répertoire de déploiement (default: /opt/mcp)
#   - IMAGE_TAG: Tag de l'image Docker à déployer
#
# Auteur: MCP Team
# Date: 17 octobre 2025
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
DEPLOY_DIR="${DEPLOY_DIR:-/opt/mcp}"
BACKUP_DIR="/opt/mcp-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="docker-compose.production.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

# Créer un backup
create_backup() {
    log "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$DEPLOY_DIR" ]; then
        if sudo tar czf "$BACKUP_DIR/mcp-backup-$TIMESTAMP.tar.gz" \
            -C "$DEPLOY_DIR" \
            "$COMPOSE_FILE" \
            .env.production \
            mcp-data/ \
            2>/dev/null; then
            log_success "Backup created: mcp-backup-$TIMESTAMP.tar.gz"
        else
            log_warning "Partial backup created (some files may be missing)"
        fi
    else
        log_warning "Deploy directory does not exist, skipping backup"
    fi
}

# Pull et déployer
deploy() {
    log "Starting deployment process..."
    
    cd "$DEPLOY_DIR" || {
        log_error "Failed to change to deploy directory: $DEPLOY_DIR"
        return 1
    }
    
    log "Pulling new images..."
    if sudo docker-compose -f "$COMPOSE_FILE" pull; then
        log_success "Images pulled successfully"
    else
        log_error "Failed to pull images"
        return 1
    fi
    
    log "Starting services..."
    if sudo docker-compose -f "$COMPOSE_FILE" up -d --remove-orphans; then
        log_success "Services started successfully"
    else
        log_error "Failed to start services"
        return 1
    fi
    
    log "Deployment complete"
    return 0
}

# Health check
health_check() {
    log "Running health check..."
    local max_attempts=10
    local attempt=1
    local wait_time=10
    
    while [ $attempt -le $max_attempts ]; do
        log "Health check attempt $attempt/$max_attempts..."
        
        # Test principal endpoint
        if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
            log_success "Health check passed - API is responding"
            return 0
        fi
        
        # Fallback sur root endpoint
        if curl -sf http://localhost:8000/ > /dev/null 2>&1; then
            log_success "Health check passed - Root endpoint is responding"
            return 0
        fi
        
        log_warning "Attempt $attempt/$max_attempts failed, waiting ${wait_time}s before retry..."
        sleep $wait_time
        attempt=$((attempt + 1))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    
    # Afficher les logs des containers pour debug
    log "Container status:"
    sudo docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" ps
    
    log "Recent API logs:"
    sudo docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" logs --tail=50 mcp-api-prod 2>/dev/null || true
    
    return 1
}

# Rollback
rollback() {
    log_error "Rolling back to previous version..."
    
    local backup_file=$(ls -t "$BACKUP_DIR"/mcp-backup-*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
        log "Restoring from backup: $backup_file"
        
        cd "$DEPLOY_DIR" || return 1
        
        # Arrêter les services actuels
        sudo docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
        
        # Restaurer le backup
        if sudo tar xzf "$backup_file" -C "$DEPLOY_DIR"; then
            log_success "Backup restored successfully"
            
            # Redémarrer les services
            if sudo docker-compose -f "$COMPOSE_FILE" up -d; then
                log_success "Services restarted with previous version"
                sleep 30
                
                # Vérifier que le rollback a fonctionné
                if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
                    log_success "Rollback successful - service is healthy"
                else
                    log_error "Rollback completed but service is not healthy"
                fi
            else
                log_error "Failed to restart services after rollback"
            fi
        else
            log_error "Failed to extract backup"
        fi
    else
        log_error "No backup found for rollback in $BACKUP_DIR"
    fi
}

# Nettoyage
cleanup() {
    log "Performing cleanup..."
    
    # Nettoyer les anciennes images Docker (plus de 72h)
    log "Cleaning old Docker images..."
    sudo docker image prune -af --filter "until=72h" 2>/dev/null || true
    
    # Garder seulement les 5 derniers backups
    log "Cleaning old backups (keeping last 5)..."
    local backups=$(ls -t "$BACKUP_DIR"/mcp-backup-*.tar.gz 2>/dev/null | tail -n +6)
    if [ -n "$backups" ]; then
        echo "$backups" | xargs -r rm
        log_success "Old backups cleaned"
    fi
    
    # Nettoyer les containers arrêtés
    sudo docker container prune -f 2>/dev/null || true
    
    # Nettoyer les volumes non utilisés
    sudo docker volume prune -f 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Afficher le statut
show_status() {
    log "=== Deployment Status ==="
    echo ""
    
    log "Container status:"
    sudo docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" ps
    echo ""
    
    log "Recent logs (last 20 lines):"
    sudo docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" logs --tail=20 mcp-api-prod 2>/dev/null || true
    echo ""
    
    log "Disk usage:"
    df -h "$DEPLOY_DIR" | tail -1
    echo ""
    
    log "Available backups:"
    ls -lh "$BACKUP_DIR"/mcp-backup-*.tar.gz 2>/dev/null | tail -5 || echo "No backups found"
    echo ""
}

# Main
main() {
    log "═══════════════════════════════════════════════"
    log "    CI/CD Deployment Started"
    log "═══════════════════════════════════════════════"
    echo ""
    
    log "Deploy directory: $DEPLOY_DIR"
    log "Backup directory: $BACKUP_DIR"
    log "Timestamp: $TIMESTAMP"
    echo ""
    
    # Étape 1: Backup
    if ! create_backup; then
        log_error "Backup creation failed (continuing anyway)"
    fi
    echo ""
    
    # Étape 2: Déploiement
    if deploy; then
        log_success "Deployment phase completed"
    else
        log_error "Deployment phase failed"
        rollback
        exit 1
    fi
    echo ""
    
    # Étape 3: Health check
    if health_check; then
        log_success "Health check passed"
    else
        log_error "Health check failed - initiating rollback"
        rollback
        exit 1
    fi
    echo ""
    
    # Étape 4: Nettoyage
    cleanup
    echo ""
    
    # Étape 5: Afficher le statut
    show_status
    
    log "═══════════════════════════════════════════════"
    log_success "    Deployment Successful!"
    log "═══════════════════════════════════════════════"
    echo ""
    
    exit 0
}

# Gestion des erreurs
trap 'log_error "Script failed at line $LINENO"' ERR

# Exécution
main "$@"

