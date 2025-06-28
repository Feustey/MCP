#!/bin/bash

# Script de déploiement sécurisé MCP sur Hostinger
# Dernière mise à jour: 7 mai 2025

set -e

# Configuration des variables d'environnement
ENV_FILE=".env.production"
DOCKER_COMPOSE_FILE="docker-compose.hostinger-production.yml"
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
REMOTE_DIR="/home/$REMOTE_USER/feustey"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
SUDO_PWD="Feustey@AI!"
SSH_KEY="$HOME/.ssh/mcp_deploy_key"
SSH_OPTIONS="-i $SSH_KEY -o StrictHostKeyChecking=no"

echo "🔒 Vérification des fichiers de configuration..."

# Vérifier l'existence du fichier .env.production
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Erreur: $ENV_FILE n'existe pas"
    echo "📝 Copiez config/env.production.template vers $ENV_FILE et configurez les variables"
    exit 1
fi

# Vérifier l'existence de la clé SSH
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Erreur: Clé SSH $SSH_KEY non trouvée"
    echo "📝 Générez une nouvelle clé avec: ssh-keygen -t ed25519 -C 'mcp-deploy' -f $SSH_KEY"
    exit 1
fi

# Créer le répertoire de backup
mkdir -p "$BACKUP_DIR"

# Configuration initiale du serveur distant
echo "🔧 Configuration initiale du serveur..."
ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
    # Créer les répertoires nécessaires avec sudo
    echo "$SUDO_PWD" | sudo -S mkdir -p $REMOTE_DIR
    echo "$SUDO_PWD" | sudo -S chown $REMOTE_USER:$REMOTE_USER $REMOTE_DIR
    
    # Vérifier Docker et Docker Compose
    if ! command -v docker &> /dev/null; then
        echo "Installation de Docker..."
        echo "$SUDO_PWD" | sudo -S apt-get update
        echo "$SUDO_PWD" | sudo -S apt-get install -y docker.io docker-compose
    fi
    
    # Ajouter l'utilisateur au groupe docker
    echo "$SUDO_PWD" | sudo -S usermod -aG docker $REMOTE_USER
    
    # Créer le répertoire pour les logs
    echo "$SUDO_PWD" | sudo -S mkdir -p /app/logs
    echo "$SUDO_PWD" | sudo -S chown -R $REMOTE_USER:$REMOTE_USER /app/logs
EOF

# Sauvegarder la configuration actuelle
echo "💾 Sauvegarde de la configuration actuelle..."
if ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" "test -d $REMOTE_DIR"; then
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" "cd $REMOTE_DIR && tar czf - ." > "$BACKUP_DIR/mcp_backup.tar.gz" || true
fi

# Transférer les fichiers nécessaires
echo "📤 Transfert des fichiers vers le serveur..."

# Créer les répertoires nécessaires sur le serveur
ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
    mkdir -p $REMOTE_DIR/config
    mkdir -p $REMOTE_DIR/app
    mkdir -p $REMOTE_DIR/src
EOF

# Copier le fichier .env.production
scp $SSH_OPTIONS "$ENV_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/.env.production"
scp $SSH_OPTIONS "$DOCKER_COMPOSE_FILE" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/docker-compose.yml"

# Transférer les répertoires
for dir in config app src; do
    echo "📁 Transfert du répertoire $dir..."
    scp $SSH_OPTIONS -r $dir/* "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/$dir/" || true
done

# Déploiement sur le serveur distant
echo "🚀 Déploiement sur le serveur..."
ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << EOF
    cd "$REMOTE_DIR"
    
    # S'assurer que le fichier .env existe
    if [ ! -f ".env.production" ]; then
        echo "❌ Erreur: .env.production non trouvé"
        exit 1
    fi
    
    # Copier .env.production vers .env
    cp .env.production .env
    
    # Charger les variables d'environnement
    set -a
    source .env
    set +a
    
    # Vérifier les services Docker existants
    echo "🔍 Vérification des services existants..."
    echo "$SUDO_PWD" | sudo -S docker-compose down --remove-orphans || true
    
    # Pull des nouvelles images
    echo "📥 Récupération des images Docker..."
    echo "$SUDO_PWD" | sudo -S docker-compose pull
    
    # Démarrage des services
    echo "🌟 Démarrage des services..."
    echo "$SUDO_PWD" | sudo -S docker-compose up -d
    
    # Vérification des services
    echo "✅ Vérification du déploiement..."
    echo "$SUDO_PWD" | sudo -S docker-compose ps
    echo "$SUDO_PWD" | sudo -S docker-compose logs --tail=50
    
    # Test de l'API
    echo "🔍 Test de l'API..."
    curl -f http://localhost:8000/health || echo "❌ L'API n'est pas accessible"
    
    # Configuration des permissions des logs
    echo "📝 Configuration des permissions des logs..."
    echo "$SUDO_PWD" | sudo -S chown -R $REMOTE_USER:$REMOTE_USER /app/logs
EOF

echo "✨ Déploiement terminé!"
echo "📝 Logs disponibles dans: $BACKUP_DIR"
echo "🌐 Vérifiez l'accès à l'API: https://api.dazno.de/health" 