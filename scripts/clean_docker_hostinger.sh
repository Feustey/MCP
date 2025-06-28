#!/bin/bash
set -e

# Configuration
REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"

echo "🧹 Nettoyage complet de l'environnement Docker sur Hostinger..."

ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Arrêt des conteneurs
    docker stop $(docker ps -aq) || true
    docker rm $(docker ps -aq) || true
    
    # Suppression des images
    docker rmi $(docker images -q) || true
    
    # Suppression des volumes et réseaux
    docker volume prune -f
    docker network prune -f
    
    # Désinstallation complète de Docker
    apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    apt-get autoremove -y
    rm -rf /var/lib/docker
    rm -rf /var/lib/containerd
    rm -f /etc/apt/sources.list.d/docker.list
    rm -f /etc/apt/keyrings/docker.asc
EOF

echo "✅ Nettoyage terminé" 