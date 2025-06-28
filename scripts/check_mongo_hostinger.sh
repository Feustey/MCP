#!/bin/bash
set -e

REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"

ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Vérification du service MongoDB
    systemctl status mongod || true
    # Vérification du port d'écoute
    netstat -tulpn | grep mongo || true
    # Vérification de la version
    mongod --version || true
EOF 