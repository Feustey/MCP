#!/bin/bash
# Script pour synchroniser les fichiers vers le serveur de production
# Inclut les nouvelles fonctionnalités de rapport Daznode

set -e

# Configuration
SSH_HOST="feustey@147.79.101.32"
SSH_PASSWORD="Feustey@AI!"
REMOTE_DIR="~/mcp"
LOCAL_DIR="."

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Test de connexion SSH
test_connection() {
    log "🔐 Test de la connexion SSH..."
    
    if sshpass -p "$SSH_PASSWORD" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $SSH_HOST "echo 'Connexion réussie'" &> /dev/null; then
        log "✅ Connexion SSH opérationnelle"
    else
        echo "❌ Impossible de se connecter à $SSH_HOST"
        echo "Vérifiez vos credentials SSH"
        exit 1
    fi
}

# Synchronisation des fichiers
sync_files() {
    log "📁 Synchronisation des fichiers vers le serveur..."
    
    # Créer le répertoire distant si nécessaire
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_HOST "mkdir -p $REMOTE_DIR"
    
    # Fichiers essentiels à synchroniser
    info "Synchronisation du code source..."
    sshpass -p "$SSH_PASSWORD" rsync -avz --progress \
        --exclude=".git/" \
        --exclude="__pycache__/" \
        --exclude="*.pyc" \
        --exclude=".env.local" \
        --exclude="venv/" \
        --exclude="venv_rag/" \
        --exclude="logs/" \
        --exclude="backups/" \
        --exclude=".pytest_cache/" \
        --exclude="node_modules/" \
        -e "ssh -o StrictHostKeyChecking=no" \
        $LOCAL_DIR/ $SSH_HOST:$REMOTE_DIR/
    
    log "✅ Synchronisation terminée"
}

# Vérification des nouveaux fichiers
verify_new_files() {
    log "🔍 Vérification des nouveaux fichiers de rapport..."
    
    # Vérifier que les nouveaux scripts sont présents
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_HOST "test -f $REMOTE_DIR/scripts/daily_daznode_report.py"; then
        log "✅ Script de rapport Daznode synchronisé"
    else
        warn "⚠️  Script de rapport manquant"
    fi
    
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_HOST "test -f $REMOTE_DIR/scripts/remote_build_deploy.sh"; then
        log "✅ Script de déploiement distant synchronisé"
    else
        warn "⚠️  Script de déploiement distant manquant"
    fi
    
    # Rendre les scripts exécutables
    info "Configuration des permissions..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no $SSH_HOST "chmod +x $REMOTE_DIR/scripts/*.sh $REMOTE_DIR/scripts/*.py"
    
    log "✅ Permissions configurées"
}

# Affichage des instructions
show_next_steps() {
    log "📋 Étapes suivantes pour le déploiement:"
    echo
    echo "1. Se connecter au serveur:"
    echo "   ssh $SSH_HOST"
    echo
    echo "2. Aller dans le répertoire du projet:"
    echo "   cd $REMOTE_DIR"
    echo
    echo "3. Exécuter le déploiement complet:"
    echo "   ./scripts/remote_build_deploy.sh"
    echo
    echo "OU en une seule commande:"
    echo "   sshpass -p '$SSH_PASSWORD' ssh -o StrictHostKeyChecking=no $SSH_HOST 'cd $REMOTE_DIR && ./scripts/remote_build_deploy.sh'"
    echo
    echo "🔍 Pour surveiller le déploiement:"
    echo "   ssh $SSH_HOST 'cd $REMOTE_DIR && tail -f logs/daznode_report.log'"
}

# Fonction principale
main() {
    log "🚀 Synchronisation vers le serveur de production"
    log "Serveur: $SSH_HOST"
    log "Répertoire distant: $REMOTE_DIR"
    echo
    
    test_connection
    sync_files
    verify_new_files
    
    log "✅ Synchronisation terminée avec succès!"
    echo
    show_next_steps
}

main "$@"