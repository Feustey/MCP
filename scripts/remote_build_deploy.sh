#!/bin/bash
# Script à exécuter directement sur le serveur Hostinger
# Fait le build et le déploiement avec les nouvelles fonctionnalités

set -e

# Configuration
PROJECT_DIR="$HOME/mcp"
DOCKER_IMAGE="feustey/dazno"
BUILD_TAG=$(date +%Y%m%d-%H%M)
BACKUP_DIR="$HOME/mcp_backup_$(date +%Y%m%d_%H%M)"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Vérifications initiales
check_environment() {
    log "🔍 Vérification de l'environnement..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
    fi
    
    # Vérifier le répertoire du projet
    if [ ! -d "$PROJECT_DIR" ]; then
        error "Répertoire de projet non trouvé: $PROJECT_DIR"
    fi
    
    cd "$PROJECT_DIR"
    
    log "✅ Environnement validé"
}

# Sauvegarde avant déploiement
backup_current_state() {
    log "💾 Sauvegarde de l'état actuel..."
    
    # Créer la sauvegarde
    mkdir -p "$BACKUP_DIR"
    
    # Sauvegarder la configuration
    if [ -f docker-compose.hostinger-production.yml ]; then
        cp docker-compose.hostinger-production.yml "$BACKUP_DIR/"
    fi
    
    # Sauvegarder les logs récents
    if [ -d logs ]; then
        cp -r logs "$BACKUP_DIR/"
    fi
    
    # Sauvegarder les variables d'environnement
    if [ -f .env.production ]; then
        cp .env.production "$BACKUP_DIR/"
    fi
    
    log "✅ Sauvegarde créée dans $BACKUP_DIR"
}

# Mise à jour du code
update_codebase() {
    log "📥 Mise à jour du code source..."
    
    # Si c'est un repo Git, faire un pull
    if [ -d .git ]; then
        info "Pull des dernières modifications Git..."
        git fetch origin
        git pull origin main || git pull origin master || warn "Impossible de faire le pull Git"
    else
        warn "Pas de repo Git détecté - Assurez-vous que le code est à jour"
    fi
    
    # Vérifier que les nouveaux scripts sont présents
    if [ ! -f "scripts/daily_daznode_report.py" ]; then
        warn "Script de rapport Daznode non trouvé - Fonctionnalités de rapport non disponibles"
    else
        log "✅ Nouveaux scripts de rapport détectés"
    fi
}

# Construction locale de l'image
build_image_locally() {
    log "🔨 Construction de l'image Docker..."
    
    # Nettoyer les anciennes images
    info "Nettoyage des anciennes images..."
    docker system prune -f --filter "until=48h" || true
    
    # Construire la nouvelle image
    if [ -f Dockerfile.production ]; then
        info "Construction avec Dockerfile.production"
        docker build -f Dockerfile.production -t $DOCKER_IMAGE:$BUILD_TAG -t $DOCKER_IMAGE:latest .
    elif [ -f Dockerfile ]; then
        info "Construction avec Dockerfile par défaut"
        docker build -t $DOCKER_IMAGE:$BUILD_TAG -t $DOCKER_IMAGE:latest .
    else
        error "Aucun Dockerfile trouvé"
    fi
    
    log "✅ Image construite: $DOCKER_IMAGE:$BUILD_TAG"
}

# Arrêt des services actuels
stop_current_services() {
    log "🛑 Arrêt des services actuels..."
    
    # Identifier le fichier docker-compose à utiliser
    COMPOSE_FILE=""
    if [ -f docker-compose.hostinger-production.yml ]; then
        COMPOSE_FILE="docker-compose.hostinger-production.yml"
    elif [ -f docker-compose.prod.yml ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
    elif [ -f docker-compose.yml ]; then
        COMPOSE_FILE="docker-compose.yml"
    else
        warn "Aucun fichier docker-compose trouvé"
        return
    fi
    
    info "Utilisation de $COMPOSE_FILE"
    docker-compose -f $COMPOSE_FILE down --remove-orphans || warn "Erreur lors de l'arrêt"
    
    log "✅ Services arrêtés"
}

# Mise à jour de la configuration Docker Compose
update_docker_compose() {
    log "⚙️  Mise à jour de la configuration Docker Compose..."
    
    # Backup du fichier actuel
    if [ -f docker-compose.hostinger-production.yml ]; then
        cp docker-compose.hostinger-production.yml docker-compose.hostinger-production.yml.backup
        
        # Mettre à jour le tag de l'image
        info "Mise à jour du tag d'image vers $BUILD_TAG"
        sed -i "s|image: $DOCKER_IMAGE:.*|image: $DOCKER_IMAGE:$BUILD_TAG|g" docker-compose.hostinger-production.yml
        
        log "✅ Configuration mise à jour"
    else
        warn "Fichier docker-compose.hostinger-production.yml non trouvé"
    fi
}

# Démarrage des nouveaux services
start_new_services() {
    log "🚀 Démarrage des nouveaux services..."
    
    # Démarrer avec le nouveau tag
    if [ -f docker-compose.hostinger-production.yml ]; then
        docker-compose -f docker-compose.hostinger-production.yml up -d
    else
        error "Fichier docker-compose non trouvé"
    fi
    
    # Attendre le démarrage
    info "Attente du démarrage des services..."
    sleep 15
    
    log "✅ Services démarrés"
}

# Vérification du déploiement
verify_deployment() {
    log "🧪 Vérification du déploiement..."
    
    # Vérifier les conteneurs
    info "État des conteneurs:"
    docker-compose -f docker-compose.hostinger-production.yml ps
    
    # Test de l'API
    info "Test de l'endpoint de santé..."
    if curl -f http://localhost:8000/health &> /dev/null; then
        log "✅ API fonctionnelle"
    else
        warn "⚠️  Endpoint de santé non accessible"
    fi
    
    # Vérifier les logs
    info "Logs récents de l'API:"
    docker-compose -f docker-compose.hostinger-production.yml logs --tail=10 mcp-api-prod || true
}

# Installation du cron pour les rapports
install_cron_reports() {
    log "⏰ Configuration de la planification des rapports..."
    
    # Vérifier que le script existe dans le conteneur
    if docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod test -f scripts/daily_daznode_report.py; then
        info "Script de rapport trouvé dans le conteneur"
        
        # Configurer le cron
        CRON_ENTRY="0 7 * * * cd $PROJECT_DIR && docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1"
        
        # Supprimer l'ancienne entrée si elle existe
        crontab -l 2>/dev/null | grep -v "daily_daznode_report.py" | crontab - || true
        
        # Ajouter la nouvelle entrée
        (crontab -l 2>/dev/null; echo "# Rapport quotidien Daznode - 7h00"; echo "$CRON_ENTRY") | crontab -
        
        log "✅ Planification configurée pour 7h00 tous les jours"
    else
        warn "⚠️  Script de rapport non trouvé dans le conteneur - Rapports non configurés"
    fi
}

# Test du rapport (optionnel)
test_report_generation() {
    log "📊 Test de génération du rapport..."
    
    if docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py; then
        log "✅ Test de génération du rapport réussi"
    else
        warn "⚠️  Problème lors du test - Vérifiez les variables d'environnement Telegram"
    fi
}

# Rollback en cas d'échec
rollback() {
    error_msg="$1"
    warn "🔄 Rollback en cours suite à l'erreur: $error_msg"
    
    if [ -d "$BACKUP_DIR" ]; then
        info "Restauration depuis $BACKUP_DIR"
        
        # Restaurer la configuration
        if [ -f "$BACKUP_DIR/docker-compose.hostinger-production.yml" ]; then
            cp "$BACKUP_DIR/docker-compose.hostinger-production.yml" .
        fi
        
        # Redémarrer les anciens services
        docker-compose -f docker-compose.hostinger-production.yml up -d || true
        
        warn "⚠️  Rollback effectué - Vérifiez les services"
    fi
    
    exit 1
}

# Fonction principale
main() {
    log "🚀 Déploiement MCP Daznode avec nouvelles fonctionnalités"
    log "================================================================"
    
    # Gestion des erreurs avec rollback
    trap 'rollback "Erreur durant le déploiement"' ERR
    
    # Étapes du déploiement
    check_environment
    backup_current_state
    update_codebase
    build_image_locally
    stop_current_services
    update_docker_compose
    start_new_services
    verify_deployment
    install_cron_reports
    
    # Test optionnel
    echo
    read -p "Tester la génération du rapport maintenant ? (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[OoYy]$ ]]; then
        test_report_generation
    fi
    
    log "================================================================"
    log "🎉 Déploiement terminé avec succès!"
    log ""
    log "📊 Nouvelles fonctionnalités ajoutées:"
    log "  ✅ Rapport quotidien Daznode (7h00 tous les jours)"
    log "  ✅ KPI complets du nœud Lightning"
    log "  ✅ Recommandations automatiques"
    log "  ✅ Notifications Telegram enrichies"
    log ""
    log "🔍 Vérifications:"
    log "  • API: curl http://localhost:8000/health"
    log "  • Services: docker-compose -f docker-compose.hostinger-production.yml ps"
    log "  • Logs: tail -f logs/daznode_report.log"
    log "  • Cron: crontab -l | grep daznode"
    log ""
    log "💡 Sauvegarde disponible dans: $BACKUP_DIR"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi