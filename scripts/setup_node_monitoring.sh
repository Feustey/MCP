#!/bin/bash

# Configuration du monitoring pour le nœud daznode
DAZNODE_PUBKEY="02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"

# Création des répertoires nécessaires
mkdir -p rag/RAG_assets/nodes/${DAZNODE_PUBKEY}/raw_data
mkdir -p rag/RAG_assets/reports/${DAZNODE_PUBKEY}
mkdir -p data/metrics/${DAZNODE_PUBKEY}

# Configuration des permissions
chmod 755 rag/RAG_assets/nodes/${DAZNODE_PUBKEY}
chmod 755 rag/RAG_assets/reports/${DAZNODE_PUBKEY}
chmod 755 data/metrics/${DAZNODE_PUBKEY}

# Ajout de la tâche cron pour l'analyse quotidienne
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/python3 $(pwd)/scripts/daily_node_analysis.py ${DAZNODE_PUBKEY} >> $(pwd)/logs/node_scanner_cron.log 2>&1") | crontab -

# Initialisation du fichier de log
touch logs/node_scanner_cron.log
chmod 644 logs/node_scanner_cron.log

echo "Configuration du monitoring pour daznode terminée" 