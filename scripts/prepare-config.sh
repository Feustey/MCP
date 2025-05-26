#!/bin/bash
# Script de préparation des configurations pour MCP
# Dernière mise à jour: 27 mai 2025

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Charger les variables d'environnement
if [[ -f "$PROJECT_ROOT/.env.production" ]]; then
    source "$PROJECT_ROOT/.env.production"
else
    echo "Erreur: Fichier .env.production manquant"
    exit 1
fi

echo "=== Préparation des configurations ==="

# Remplacer le mot de passe Redis dans la configuration
if [[ -f "$PROJECT_ROOT/config/redis/redis-prod.conf" ]]; then
    echo "Configuration de Redis..."
    sed -i.bak "s/placeholder_password_will_be_replaced/${REDIS_PASSWORD}/g" \
        "$PROJECT_ROOT/config/redis/redis-prod.conf"
    echo "✓ Configuration Redis mise à jour"
else
    echo "⚠️  Configuration Redis non trouvée"
fi

# Créer le script d'initialisation MongoDB si nécessaire
if [[ ! -f "$PROJECT_ROOT/config/mongodb/init-mongo.js" ]]; then
    echo "Création du script d'initialisation MongoDB..."
    cat > "$PROJECT_ROOT/config/mongodb/init-mongo.js" << EOF
// Script d'initialisation MongoDB pour MCP Production
// Créé automatiquement le $(date)

db = db.getSiblingDB('mcp_prod');

// Créer l'utilisateur applicatif
db.createUser({
  user: '${MONGO_ROOT_USER}',
  pwd: '${MONGO_ROOT_PASSWORD}',
  roles: [
    { role: 'readWrite', db: 'mcp_prod' },
    { role: 'dbAdmin', db: 'mcp_prod' }
  ]
});

// Créer les collections de base
db.createCollection('nodes');
db.createCollection('metrics');
db.createCollection('reports');
db.createCollection('actions');

// Créer les index de base
db.nodes.createIndex({ "public_key": 1 }, { unique: true });
db.metrics.createIndex({ "timestamp": 1 });
db.reports.createIndex({ "created_at": 1 });

print('✓ Base de données MCP initialisée');
EOF
    echo "✓ Script d'initialisation MongoDB créé"
fi

# Créer les répertoires de données nécessaires
echo "Création des répertoires de données..."
mkdir -p "$PROJECT_ROOT"/{logs,data,backups}
mkdir -p "$PROJECT_ROOT/rag/RAG_assets"/{logs,reports,metrics}

# Créer le répertoire des logs s'il n'existe pas
mkdir -p "/tmp/mcp_logs"

echo "✓ Préparation terminée avec succès" 