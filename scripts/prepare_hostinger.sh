#!/bin/bash
set -e

REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"

echo "🔧 Préparation de l'environnement Hostinger..."

# Vérification si MongoDB est installé
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "command -v mongod" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "📦 MongoDB n'est pas installé. Installation en cours..."
    ./scripts/install_mongo_hostinger.sh
else
    echo "✅ MongoDB est déjà installé"
fi

# Vérification et configuration de MongoDB
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Vérification du statut de MongoDB
    if ! systemctl is-active --quiet mongod; then
        echo "🔄 Redémarrage de MongoDB..."
        systemctl restart mongod
    fi

    # Vérification de la base MCP
    echo "🔍 Vérification de la base MCP..."
    mongosh --eval '
        if (!db.getSiblingDB("mcp").getCollectionNames().length) {
            db.getSiblingDB("mcp").createCollection("init");
            print("Base MCP créée");
        } else {
            print("Base MCP existe déjà");
        }
    '

    # Vérification de la configuration réseau
    if ! grep -q "bindIp: 0.0.0.0" /etc/mongod.conf; then
        echo "⚙️ Mise à jour de la configuration réseau..."
        sed -i 's/bindIp: 127.0.0.1/bindIp: 0.0.0.0/' /etc/mongod.conf
        systemctl restart mongod
    fi

    echo "✅ Configuration MongoDB vérifiée"
EOF

echo "✅ Environnement Hostinger préparé avec succès" 