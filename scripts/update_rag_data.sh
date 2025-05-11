#!/bin/bash

# Script pour mettre à jour les données RAG
# À exécuter périodiquement via cron

# Définir le répertoire de base
BASE_DIR=$(dirname $(dirname $(realpath $0)))
cd $BASE_DIR

# Configurer l'environnement
source venv/bin/activate

# Timestamp pour le dossier de sauvegarde
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SNAPSHOT_DIR="rag/RAG_assets/market_data/network_snapshots/${TIMESTAMP}"

# Créer le répertoire de sauvegarde
mkdir -p $SNAPSHOT_DIR

echo "Début de la mise à jour des données RAG à $(date)"

# Exécuter l'agrégation des données
python3 run_aggregation.py

# Copier les données dans le répertoire de sauvegarde
cp -r collected_data/*.json $SNAPSHOT_DIR/

# Mettre à jour le lien symbolique vers les données les plus récentes
rm -f rag/RAG_assets/market_data/network_snapshots/latest
ln -s $SNAPSHOT_DIR rag/RAG_assets/market_data/network_snapshots/latest

# Enregistrer la date de mise à jour
date > rag/RAG_assets/market_data/network_snapshots/last_update.txt

echo "Mise à jour des données RAG terminée à $(date)"
echo "Données sauvegardées dans $SNAPSHOT_DIR"

# Nettoyer les anciens snapshots (garder seulement les 5 plus récents)
cd rag/RAG_assets/market_data/network_snapshots/
ls -td 20* | tail -n +6 | xargs -I {} rm -rf {} 2>/dev/null
cd $BASE_DIR

# Désactiver l'environnement virtuel
deactivate

echo "Script terminé avec succès" 