#!/bin/bash
set -e

REMOTE_USER="root"
REMOTE_HOST="147.79.101.32"
REMOTE_PORT="22"

echo "🔧 Installation de MongoDB sur Hostinger..."

ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
    # Installation des dépendances
    apt-get update
    apt-get install -y gnupg curl

    # Ajout de la clé MongoDB
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
        gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
        --dearmor

    # Ajout du repository MongoDB
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
        tee /etc/apt/sources.list.d/mongodb-org-7.0.list

    # Installation de MongoDB
    apt-get update
    apt-get install -y mongodb-org

    # Création du répertoire de données
    mkdir -p /data/db
    chown -R mongodb:mongodb /data/db

    # Configuration de MongoDB pour écouter sur toutes les interfaces
    cat > /etc/mongod.conf << 'EOL'
# mongod.conf

# for documentation of all options, see:
#   http://docs.mongodb.org/manual/reference/configuration-options/

# Where and how to store data.
storage:
  dbPath: /data/db

# where to write logging data.
systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

# network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0

# how the process runs
processManagement:
  timeZoneInfo: /usr/share/zoneinfo

security:
  authorization: disabled
EOL

    # Création du répertoire de logs
    mkdir -p /var/log/mongodb
    chown -R mongodb:mongodb /var/log/mongodb

    # Démarrage du service MongoDB
    systemctl daemon-reload
    systemctl enable mongod
    systemctl start mongod

    # Installation de mongosh
    apt-get install -y mongodb-mongosh

    # Vérification du statut
    echo "🔍 Vérification du statut MongoDB..."
    systemctl status mongod --no-pager
    
    # Vérification de la connexion
    echo "🔍 Test de connexion MongoDB..."
    mongosh --eval "db.version()"

    # Création de la base MCP
    echo "📦 Création de la base MCP..."
    mongosh --eval '
        if (!db.getSiblingDB("mcp").getCollectionNames().length) {
            db.getSiblingDB("mcp").createCollection("init");
            print("Base MCP créée");
        } else {
            print("Base MCP existe déjà");
        }
    '

    # Vérification des ports
    echo "🔍 Vérification des ports..."
    netstat -tulpn | grep mongo
EOF

echo "✅ MongoDB installé et configuré avec succès" 