#!/bin/bash
set -e

# Fonction pour afficher les messages de log
log() {
  echo "[$(date --rfc-3339=seconds)] $*"
}

# Démarrer MongoDB
log "Démarrage de MongoDB..."
mkdir -p /data/db
# Cette approche permet de ne pas bloquer le script principal
mongod --fork --logpath /var/log/mongodb/mongod.log || log "MongoDB est peut-être déjà en cours d'exécution"
log "MongoDB démarré."

# Démarrer Redis
log "Démarrage de Redis..."
redis-server --daemonize yes
log "Redis démarré."

# Attendre que les services soient prêts
log "Attente de la disponibilité des services..."
sleep 5

# Vérification de Redis
log "Vérification de Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    log "Erreur: Redis n'est pas disponible"
    exit 1
fi
log "Redis est opérationnel."

# Vérification de MongoDB
log "Vérification de MongoDB..."
if ! mongo --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    log "Erreur: MongoDB n'est pas disponible"
    exit 1
fi
log "MongoDB est opérationnel."

# Exécuter un script de simulation initial pour générer des données
log "Génération des données de simulation..."
python src/tools/node_simulator.py

# Démarrer l'application FastAPI avec uvicorn
log "Démarrage de l'API FastAPI..."
cd /app
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload 