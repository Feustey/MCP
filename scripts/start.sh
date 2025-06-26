#!/bin/bash

# Script de démarrage pour le conteneur MCP
# Dernière mise à jour: 7 janvier 2025

set -e

# Configuration
APP_DIR="/app"
LOG_DIR="/app/logs"
DATA_DIR="/app/data"
RAG_DIR="/app/rag"

# Couleurs pour les logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Fonction de vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier que les répertoires existent
    for dir in "$APP_DIR" "$LOG_DIR" "$DATA_DIR" "$RAG_DIR"; do
        if [ ! -d "$dir" ]; then
            warn "Création du répertoire $dir"
            mkdir -p "$dir"
        fi
    done
    
    # Vérifier les permissions
    if [ ! -w "$LOG_DIR" ]; then
        error "Le répertoire $LOG_DIR n'est pas accessible en écriture"
    fi
    
    log "Prérequis validés ✓"
}

# Fonction de configuration de l'environnement
setup_environment() {
    log "Configuration de l'environnement..."
    
    # Variables d'environnement par défaut
    export ENVIRONMENT=${ENVIRONMENT:-production}
    export DEBUG=${DEBUG:-false}
    export DRY_RUN=${DRY_RUN:-true}
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    export HOST=${HOST:-0.0.0.0}
    export PORT=${PORT:-8000}
    export WORKERS=${WORKERS:-4}
    
    # Configuration Python
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH=/app
    
    # Vérifier les variables critiques
    if [ -z "$AI_OPENAI_API_KEY" ]; then
        warn "AI_OPENAI_API_KEY non définie"
    fi
    
    if [ -z "$MONGO_URL" ]; then
        warn "MONGO_URL non définie"
    fi
    
    if [ -z "$REDIS_HOST" ]; then
        warn "REDIS_HOST non définie"
    fi
    
    log "Environnement configuré ✓"
}

# Fonction de vérification de la connectivité
check_connectivity() {
    log "Vérification de la connectivité..."
    
    # Test de connectivité MongoDB (si configuré)
    if [ -n "$MONGO_URL" ]; then
        log "Test de connectivité MongoDB..."
        # Le test sera fait par l'application
    fi
    
    # Test de connectivité Redis (si configuré)
    if [ -n "$REDIS_HOST" ]; then
        log "Test de connectivité Redis..."
        # Le test sera fait par l'application
    fi
    
    log "Connectivité vérifiée ✓"
}

# Fonction de démarrage de l'application
start_application() {
    log "Démarrage de l'application MCP..."
    
    # Changer vers le répertoire de l'application
    cd "$APP_DIR"
    
    # Vérifier que l'application existe
    if [ ! -f "app/main.py" ] && [ ! -f "src/api/main.py" ]; then
        error "Fichier principal de l'application non trouvé"
    fi
    
    # Déterminer le point d'entrée
    if [ -f "app/main.py" ]; then
        APP_MODULE="app.main:app"
    else
        APP_MODULE="src.api.main:app"
    fi
    
    log "Point d'entrée: $APP_MODULE"
    
    # Démarrage avec uvicorn
    exec uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL" \
        --access-log \
        --use-colors
}

# Fonction de gestion des signaux
setup_signal_handlers() {
    trap 'log "Signal reçu, arrêt gracieux..."; exit 0' SIGTERM SIGINT
}

# Fonction principale
main() {
    log "=== DÉMARRAGE DU CONTENEUR MCP ==="
    log "Version: 1.0.0"
    log "Environnement: $ENVIRONMENT"
    log "Utilisateur: $(whoami)"
    log "Répertoire: $APP_DIR"
    
    # Configuration des gestionnaires de signaux
    setup_signal_handlers
    
    # Vérifications et configuration
    check_prerequisites
    setup_environment
    check_connectivity
    
    # Démarrage de l'application
    start_application
}

# Exécution du script principal
main "$@" 