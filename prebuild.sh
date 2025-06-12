#!/bin/bash
set -e

echo "Vérification des fichiers critiques pour le build Docker..."

for f in config/gunicorn/gunicorn.conf.py scripts/entrypoint-prod.sh; do
    if [ ! -f "$f" ]; then
        echo "❌ Fichier manquant : $f"
        exit 1
    else
        echo "✅ $f présent"
    fi
done

echo "Tous les fichiers critiques sont présents."