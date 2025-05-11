#!/bin/bash

# Script pour nettoyer les environnements virtuels
# À exécuter après avoir validé que l'environnement principal fonctionne correctement

echo "Nettoyage des environnements virtuels..."

# Vérifier si nous sommes dans un environnement virtuel actif
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "⚠️ ATTENTION: Vous êtes actuellement dans un environnement virtuel actif."
    echo "Désactivez-le d'abord avec 'deactivate' avant d'exécuter ce script."
    exit 1
fi

# Vérifier que l'environnement principal existe
if [ ! -d "venv" ]; then
    echo "❌ Erreur: L'environnement principal 'venv' n'existe pas."
    echo "Créez-le d'abord avec 'python -m venv venv'."
    exit 1
fi

# Supprimer l'environnement secondaire s'il existe
if [ -d "venv_new" ]; then
    echo "Suppression de l'environnement venv_new..."
    rm -rf venv_new
    echo "✓ Environnement venv_new supprimé."
fi

# Supprimer d'autres environnements potentiels
for env in lnbits-env lnbits-env-new .venv; do
    if [ -d "$env" ]; then
        echo "Suppression de l'environnement $env..."
        rm -rf "$env"
        echo "✓ Environnement $env supprimé."
    fi
done

echo "✅ Nettoyage des environnements virtuels terminé."
echo "Un seul environnement 'venv' est maintenant disponible." 