#!/bin/bash
# Script de déploiement cloud MCP
# Usage : ./deploy_cloud.sh

set -e

# 1. Construction des images Docker (optionnel si images déjà buildées)
echo "[MCP] Construction des images Docker locales..."
docker compose -f docker-compose.yml build

# 2. Lancement des services principaux
# (adapter le fichier docker-compose.yml pour le cloud si besoin)
echo "[MCP] Lancement des services MCP (API, RAG, DB, monitoring)..."
docker compose -f docker-compose.yml up -d

echo "[MCP] Déploiement cloud MCP terminé."
# Pour l'intégration Watchtower/Nomad, voir la documentation technique. 