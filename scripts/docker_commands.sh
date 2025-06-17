#!/bin/bash

# Script pour gérer les commandes Docker Compose

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction pour afficher les messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERREUR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ATTENTION: $1${NC}"
}

# Vérifier les variables d'environnement
check_env() {
    log "Vérification des variables d'environnement..."
    
    if [ -z "$REDIS_URL" ]; then
        error "REDIS_URL non définie"
        return 1
    fi
    
    if [ -z "$MONGODB_URL" ] || [ -z "$MONGODB_USER" ] || [ -z "$MONGODB_PASSWORD" ]; then
        error "Variables MongoDB manquantes"
        return 1
    fi
    
    log "Variables d'environnement OK"
    return 0
}

# Démarrer les services
start_services() {
    log "Démarrage des services..."
    docker compose up -d
    if [ $? -eq 0 ]; then
        log "Services démarrés avec succès"
        return 0
    else
        error "Échec du démarrage des services"
        return 1
    fi
}

# Arrêter les services
stop_services() {
    log "Arrêt des services..."
    docker compose down
    if [ $? -eq 0 ]; then
        log "Services arrêtés avec succès"
        return 0
    else
        error "Échec de l'arrêt des services"
        return 1
    fi
}

# Reconstruire les services
rebuild_services() {
    log "Reconstruction des services..."
    docker compose build --no-cache
    if [ $? -eq 0 ]; then
        log "Services reconstruits avec succès"
        return 0
    else
        error "Échec de la reconstruction des services"
        return 1
    fi
}

# Vérifier l'état des services
check_services() {
    log "Vérification de l'état des services..."
    docker compose ps
}

# Afficher les logs
show_logs() {
    log "Affichage des logs..."
    docker compose logs -f
}

# Nettoyer les volumes
clean_volumes() {
    warn "Cette action va supprimer toutes les données persistantes. Êtes-vous sûr ? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log "Suppression des volumes..."
        docker compose down -v
        if [ $? -eq 0 ]; then
            log "Volumes supprimés avec succès"
            return 0
        else
            error "Échec de la suppression des volumes"
            return 1
        fi
    else
        log "Opération annulée"
        return 0
    fi
}

# Afficher l'aide
show_help() {
    echo "Usage: $0 [commande]"
    echo ""
    echo "Commandes disponibles:"
    echo "  start     - Démarrer les services"
    echo "  stop      - Arrêter les services"
    echo "  restart   - Redémarrer les services"
    echo "  rebuild   - Reconstruire les services"
    echo "  status    - Vérifier l'état des services"
    echo "  logs      - Afficher les logs"
    echo "  clean     - Nettoyer les volumes"
    echo "  help      - Afficher cette aide"
}

# Fonction principale
main() {
    case "$1" in
        "start")
            check_env && start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services && start_services
            ;;
        "rebuild")
            check_env && rebuild_services && start_services
            ;;
        "status")
            check_services
            ;;
        "logs")
            show_logs
            ;;
        "clean")
            clean_volumes
            ;;
        "help"|"")
            show_help
            ;;
        *)
            error "Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

# Exécuter le script
main "$@" 