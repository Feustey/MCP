#!/bin/bash

# Variables de configuration
USER=feustey
HOST=147.79.101.32
REMOTE_DIR=/home/feustey/MCP/config/backup
LOCAL_DIR=./config/backup

# Couleurs pour les messages
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages d'état
log_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Vérification de la présence de sshpass
if ! command -v sshpass &> /dev/null; then
    log_error "sshpass n'est pas installé. Installez-le avec 'brew install sshpass' sur macOS ou 'apt-get install sshpass' sur Linux."
fi

# Synchronisation du dossier backup
log_message "Synchronisation des fichiers vers $USER@$HOST:$REMOTE_DIR"
sshpass -p 'Feustey@AI!' rsync -avz --progress -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10" \
    $LOCAL_DIR/ \
    $USER@$HOST:$REMOTE_DIR/ || log_error "Échec de la synchronisation"

# Build et lancement du conteneur sur le serveur distant
log_message "Connexion au serveur distant et lancement du build Docker"
sshpass -p 'Feustey@AI!' ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USER@$HOST "
    cd $REMOTE_DIR
    if ! docker compose build; then
        echo 'Échec du build Docker'
        exit 1
    fi
    if ! docker compose up -d; then
        echo 'Échec du démarrage des conteneurs'
        exit 1
    fi
    echo 'Déploiement terminé avec succès'
" || log_error "Échec de l'exécution des commandes distantes"

log_message "Déploiement terminé avec succès !" 