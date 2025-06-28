#!/bin/bash

# Script de configuration des services sur Hostinger

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Fonction pour afficher les messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERREUR: $1${NC}"
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

# Configurer Redis
configure_redis() {
    log "Configuration de Redis..."
    python3 scripts/configure_redis.py
    if [ $? -eq 0 ]; then
        log "Redis configuré avec succès"
        return 0
    else
        error "Échec de la configuration de Redis"
        return 1
    fi
}

# Configurer MongoDB
configure_mongodb() {
    log "Configuration de MongoDB..."
    python3 scripts/configure_mongodb.py
    if [ $? -eq 0 ]; then
        log "MongoDB configuré avec succès"
        return 0
    else
        error "Échec de la configuration de MongoDB"
        return 1
    fi
}

# Fonction principale
main() {
    log "Démarrage de la configuration des services..."
    
    # Vérifier les variables d'environnement
    check_env || exit 1
    
    # Configurer Redis
    configure_redis || exit 1
    
    # Configurer MongoDB
    configure_mongodb || exit 1
    
    log "Configuration terminée avec succès!"
}

# Exécuter le script
main 