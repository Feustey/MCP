#!/bin/bash
# Script de nettoyage des anciens scripts de déploiement
# Dernière mise à jour: 27 mai 2025

set -e

echo "🧹 Nettoyage des anciens scripts de déploiement..."

# Liste des scripts à supprimer
SCRIPTS_TO_REMOVE=(
    "deploy_hostinger.sh"
    "deploy_hostinger_production.sh"
    "deploy_minimal.sh"
    "deploy_final.sh"
    "deploy-hostinger.sh"
    "deploy-hostinger-simple.sh"
    "deploy-hostinger-final.sh"
    "deploy_docker_hostinger.sh"
    "deploy-docker-hostinger.sh"
    "deploy_api_dazno_complete.sh"
    "fix_and_deploy_mcp.sh"
)

# Sauvegarde des scripts avant suppression
BACKUP_DIR="scripts/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

for script in "${SCRIPTS_TO_REMOVE[@]}"; do
    if [ -f "scripts/$script" ]; then
        echo "📦 Sauvegarde de $script..."
        cp "scripts/$script" "$BACKUP_DIR/"
        echo "🗑️ Suppression de $script..."
        rm "scripts/$script"
    fi
done

echo "✅ Nettoyage terminé"
echo "📁 Sauvegarde des scripts dans: $BACKUP_DIR" 