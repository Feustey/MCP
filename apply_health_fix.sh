#!/bin/bash
# Script complet pour corriger l'endpoint /health en production
# 1. Copie le fichier corrigé sur le serveur
# 2. Applique la correction via expect

set -e

echo "🔧 Correction de l'endpoint /health - Production"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier que nginx-docker.conf existe
if [ ! -f "nginx-docker.conf" ]; then
    echo "❌ Fichier nginx-docker.conf non trouvé"
    exit 1
fi

echo "📤 Étape 1/2: Copie du fichier corrigé sur le serveur..."
echo ""

# Copier le fichier via SCP
scp nginx-docker.conf feustey@147.79.101.32:/home/feustey/MCP/nginx-docker.conf

if [ $? -eq 0 ]; then
    echo "✅ Fichier copié avec succès"
else
    echo "❌ Échec de la copie du fichier"
    exit 1
fi

echo ""
echo "🚀 Étape 2/2: Application de la correction via expect..."
echo ""

# Exécuter le script expect
./fix_health_endpoint_remote.exp

echo ""
echo "✅ Processus terminé !"

