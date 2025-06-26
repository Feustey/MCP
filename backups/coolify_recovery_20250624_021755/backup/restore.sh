#!/bin/bash
# Script de restauration MCP
# Dernière mise à jour: 7 mai 2025

set -e

BACKUP_NAME=${1:-"latest"}
BACKUP_DIR=${BACKUP_DIR:-"/backups"}
RESTORE_DIR="$BACKUP_DIR/$BACKUP_NAME"

echo "🔄 Restoration MCP depuis: $BACKUP_NAME"

if [[ ! -d "$RESTORE_DIR" ]]; then
    echo "❌ Sauvegarde $BACKUP_NAME introuvable"
    exit 1
fi

echo "📊 Restauration MongoDB..."
if [[ -f "$RESTORE_DIR/mongodb.tar.gz" ]]; then
    tar -xzf "$RESTORE_DIR/mongodb.tar.gz" -C /tmp/
    mongorestore --host=${MONGO_HOST:-mongodb:27017} \
                 --username=${MONGO_ROOT_USER} \
                 --password=${MONGO_ROOT_PASSWORD} \
                 --authenticationDatabase=admin \
                 --drop /tmp/dump/
    rm -rf /tmp/dump/
else
    echo "⚠️ Pas de sauvegarde MongoDB trouvée"
fi

echo "💾 Restauration Redis..."
if [[ -f "$RESTORE_DIR/redis.rdb" ]]; then
    redis-cli -h ${REDIS_HOST:-redis} -p 6379 -a "${REDIS_PASSWORD}" \
              --rdb "$RESTORE_DIR/redis.rdb"
else
    echo "⚠️ Pas de sauvegarde Redis trouvée"
fi

echo "✅ Restauration terminée" 