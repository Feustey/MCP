#!/bin/bash
# Point d'entrée du conteneur de backup
# Dernière mise à jour: 7 mai 2025

set -e

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

# Démarrage du service cron
service cron start

# Vérification des répertoires nécessaires
mkdir -p /app/backups /var/log

# Vérification des permissions des fichiers de log
touch /var/log/cron.log
chmod 0644 /var/log/cron.log

# Affichage des logs en temps réel
tail -f /var/log/cron.log

# Maintient le conteneur en vie
tail -f /dev/null 