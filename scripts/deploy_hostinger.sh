#!/bin/bash

# Script de déploiement complet pour Hostinger
# Dernière mise à jour: 9 mai 2025

set -e

echo "🚀 Déploiement complet de MCP sur Hostinger..."

# Variables
REPO_URL="https://github.com/Feustey/MCP.git"
BRANCH="berty"
APP_DIR="/home/feustey"
BACKUP_DIR="/home/feustey/backups"

# Création du répertoire de sauvegarde
mkdir -p $BACKUP_DIR

# Sauvegarde de l'ancienne installation si elle existe
if [ -d "$APP_DIR" ] && [ -d "$APP_DIR/.git" ]; then
    echo "📦 Sauvegarde de l'ancienne installation..."
    tar -czf $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz -C $APP_DIR .
fi

# Suppression de l'ancienne installation
if [ -d "$APP_DIR" ]; then
    echo "🗑️ Suppression de l'ancienne installation..."
    rm -rf $APP_DIR
fi

# Clonage du dépôt
echo "📥 Clonage du dépôt Git..."
git clone -b $BRANCH $REPO_URL $APP_DIR

# Changement vers le répertoire de l'application
cd $APP_DIR

# Configuration des permissions
echo "🔐 Configuration des permissions..."
chmod +x scripts/*.sh

# Configuration automatique
echo "⚙️ Configuration automatique..."
bash scripts/setup_hostinger.sh

echo "🎉 Déploiement terminé!"
echo ""
echo "📝 Pour démarrer l'application:"
echo "   cd $APP_DIR"
echo "   bash scripts/start_hostinger_background.sh"
echo ""
echo "📊 Pour vérifier le statut:"
echo "   bash scripts/status_hostinger.sh" 