#!/bin/bash

# Configuration du logging
LOG_DIR="/app/logs"
mkdir -p $LOG_DIR
timestamp=$(date +"%Y%m%d_%H%M%S")
log_file="$LOG_DIR/rag_services_$timestamp.log"

echo "Démarrage des services RAG à $(date)" | tee -a $log_file

# Vérification des variables d'environnement
if [ -z "$MONGO_URI" ]; then
  echo "ERREUR: MONGO_URI non défini" | tee -a $log_file
  exit 1
fi

# Chargement des nœuds connus pour le tracking
echo "Préparation de la liste des nœuds à suivre..." | tee -a $log_file
mkdir -p /app/data
if [ ! -f "/app/data/nodes_to_track.json" ]; then
  echo "Création du fichier de nœuds par défaut..." | tee -a $log_file
  echo '[
    "03864ef025fde8fb587d989186ce6a4a186895ee44a926bfc370e2c366597a3f8f",
    "02d96eadea3d780104449aca5c93461ce67c1564e2e1d73225fa67dd3b997a919b",
    "034ea80f8b148c750463546bd999bf7321a0e6dfc60aaf84bd0400a2e8d376c0f9",
    "02d4531a2f2e6e5a9033d37d548cff4834a3898e74c3abe1985b493c42ebbd707d",
    "03c2abfa93eacec04721c019644584424aab2ba4dff3ac9bdab4e9c97007491dda",
    "0279c22ed7a068d10dc1a38ae66d2d6461e269226c60258c021b1ddcdfe4b00bc4"
  ]' > /app/data/nodes_to_track.json
fi

# Démarrage du processus de collecte des données externes
echo "Démarrage de la collecte des données externes..." | tee -a $log_file
if [ "$EXTERNAL_DATA_RUN_ONCE" = "true" ]; then
  echo "Mode single-run activé pour la collecte de données" | tee -a $log_file
  python -m scripts.run_external_data_updates --node-list /app/data/nodes_to_track.json --run-once &
  external_pid=$!
  echo "Processus de collecte des données lancé (PID: $external_pid)" | tee -a $log_file
else
  echo "Mode périodique activé pour la collecte de données (intervalle: ${UPDATE_INTERVAL_SECONDS:-3600}s)" | tee -a $log_file
  python -m scripts.run_external_data_updates --node-list /app/data/nodes_to_track.json --interval ${UPDATE_INTERVAL_SECONDS:-3600} &
  external_pid=$!
  echo "Processus de collecte des données lancé (PID: $external_pid)" | tee -a $log_file
fi

# Attendre quelques instants pour la collecte initiale des données
echo "Attente de 30 secondes pour la collecte initiale des données..." | tee -a $log_file
sleep 30

# Ingestion des données externes dans le RAG
echo "Lancement de l'ingestion des données externes dans le RAG..." | tee -a $log_file
python -m rag.external_data_ingestor | tee -a $log_file

# Démarrage du processus RAG principal
echo "Démarrage du processus RAG principal..." | tee -a $log_file
if [ "$RAG_RUN_ONCE" = "true" ]; then
  echo "Mode single-run activé pour le RAG" | tee -a $log_file
  python -m rag.rag --run-once
else
  echo "Mode périodique activé pour le RAG (intervalle: ${RAG_INTERVAL_SECONDS:-3600}s)" | tee -a $log_file
  python -m rag.rag --interval ${RAG_INTERVAL_SECONDS:-3600}
fi

# En cas d'arrêt du processus RAG principal, arrêter aussi les autres processus
echo "Le processus RAG principal s'est terminé, arrêt des autres processus..." | tee -a $log_file
if [ -n "$external_pid" ]; then
  kill -TERM $external_pid 2>/dev/null || true
fi

echo "Tous les services RAG ont été arrêtés à $(date)" | tee -a $log_file 