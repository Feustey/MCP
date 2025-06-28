#!/bin/bash
# Script de restauration MCP
# Dernière mise à jour: 7 mai 2025

set -e

# Vérification des arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE=$1
TEMP_DIR="/tmp/restore_$(date +%s)"

echo "🔄 Début de la restauration depuis $BACKUP_FILE"

# Extraction
echo "📂 Extraction de la sauvegarde..."
mkdir -p "${TEMP_DIR}"
tar -xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"

# Récupération du dossier extrait
BACKUP_DIR=$(ls "${TEMP_DIR}" | head -n 1)
FULL_BACKUP_PATH="${TEMP_DIR}/${BACKUP_DIR}"

# Restauration MongoDB
echo "📥 Restauration MongoDB..."
mongorestore --host mongodb --port 27017 --db mcp "${FULL_BACKUP_PATH}/mongodb/mcp"

# Restauration Redis
echo "📥 Restauration Redis..."
redis-cli -h redis FLUSHALL
redis-cli -h redis -n 0 shutdown save
cp "${FULL_BACKUP_PATH}/redis.rdb" /data/redis.rdb
redis-cli -h redis ping

# Nettoyage
echo "🧹 Nettoyage..."
rm -rf "${TEMP_DIR}"

echo "✅ Restauration terminée avec succès !" 