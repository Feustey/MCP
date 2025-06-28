#!/bin/sh

# Script de restauration de la configuration
# Dernière mise à jour: 9 mai 2025

echo "🔄 Restauration de la configuration originale..."

if [ -f "config.py.backup" ]; then
    mv config.py.backup config.py
    echo "✅ Configuration originale restaurée"
else
    echo "❌ Aucune sauvegarde trouvée"
    exit 1
fi 