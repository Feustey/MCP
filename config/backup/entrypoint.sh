#!/bin/bash
# Point d'entrée du conteneur de backup
# Dernière mise à jour: 7 mai 2025

echo "🚀 Démarrage du service de backup MCP"

# Démarrage du cron daemon
echo "⏰ Démarrage du scheduler cron..."
crond -f -d 8 &

# Attendre que les services soient prêts
echo "⏳ Attente des services..."
sleep 30

# Sauvegarde initiale
echo "💾 Première sauvegarde..."
/usr/local/bin/backup.sh

echo "✅ Service de backup prêt"

# Garder le conteneur en vie
tail -f /dev/null 