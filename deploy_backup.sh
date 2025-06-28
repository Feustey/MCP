#!/bin/bash

# Variables à adapter
USER=feustey
HOST=147.79.101.32
REMOTE_DIR=~/MCP/config/backup
LOCAL_DIR=./config/backup

# Synchronisation du dossier backup
sshpass -p 'Feustey@AI!' rsync -avz -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10" $LOCAL_DIR/ $USER@$HOST:$REMOTE_DIR/

# Build et lancement du conteneur sur le serveur distant
sshpass -p 'Feustey@AI!' ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $USER@$HOST "
    cd $REMOTE_DIR
    docker compose build
    docker compose up -d
" 