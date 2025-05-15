#!/bin/bash
set -e

# Script d'installation rapide MCP pour Umbrel

echo "=========================================="
echo "Installation MCP pour Umbrel"
echo "=========================================="

# Vérification du volume LND
if [ ! -d "/lnd" ]; then
  echo "❌ Erreur : le volume /lnd n'est pas monté."
  echo "Vérifiez la configuration de umbrel-app.yml et le mapping du volume LND."
  exit 1
fi

# Vérification des fichiers LND
if [ ! -r /lnd/admin.macaroon ] || [ ! -r /lnd/tls.cert ]; then
  echo "❌ Erreur : Impossible de lire /lnd/admin.macaroon ou /lnd/tls.cert."
  echo "Vérifiez les permissions (lecture requise pour l'utilisateur du conteneur)."
  ls -l /lnd
  exit 1
fi

echo "✅ Volume LND et fichiers détectés."

# Copie du .env si besoin
if [ ! -f "/data/.env" ] && [ -f "/data/.env.example" ]; then
  echo "Copie du .env.example vers /data/.env..."
  cp /data/.env.example /data/.env
fi

echo "✅ Fichier .env prêt."

echo "Installation terminée. Vous pouvez maintenant démarrer MCP via l'interface Umbrel."
echo "Accédez à l'interface sur le port 8000 du dashboard." 