#!/bin/bash
set -e

# Script de démarrage des conteneurs MCP
echo "=========================================="
echo "Démarrage du système MCP"
echo "=========================================="

# Variables d'environnement
if [ "$ENVIRONMENT" = "testing" ]; then
    echo "Mode: TESTING"
    DRYRUN=true
elif [ "$ENVIRONMENT" = "simulation" ]; then
    echo "Mode: SIMULATION"
    DRYRUN=true
elif [ "$ENVIRONMENT" = "development" ]; then
    echo "Mode: DEVELOPMENT"
    if [ -z "$DRYRUN" ]; then
        DRYRUN=true
    fi
elif [ "$ENVIRONMENT" = "production" ]; then
    echo "Mode: PRODUCTION"
    if [ -z "$DRYRUN" ]; then
        echo "⚠️ WARNING: Mode production activé sans spécifier DRYRUN"
        echo "⚠️ Activation automatique du DRYRUN par sécurité"
        DRYRUN=true
    fi
else
    echo "Mode: DEFAULT (development)"
    ENVIRONMENT="development"
    DRYRUN=true
fi

# Vérification de Redis (optionnelle)
echo "Vérification de Redis..."
if command -v nc >/dev/null 2>&1; then
    if nc -z "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" 2>/dev/null; then
        echo "✅ Redis accessible"
    else
        echo "⚠️ Redis non accessible, utilisation de la configuration cloud"
    fi
else
    echo "⚠️ netcat non disponible, skip Redis check"
fi

# Vérification de MongoDB (optionnelle)
echo "Vérification de MongoDB..."
if [ -n "$MONGO_URL" ]; then
    echo "✅ MongoDB Atlas configuré"
else
    echo "⚠️ MongoDB non configuré"
fi

# Skip LND verification in production (not needed for API-only deployment)
if [ "$ENVIRONMENT" != "production" ]; then
    # Vérification des fichiers LND (développement seulement)
    if [ -d "/lnd" ] && ([ ! -r /lnd/admin.macaroon ] || [ ! -r /lnd/tls.cert ]); then
        echo "❌ Erreur: Impossible de lire les fichiers LND (/lnd/admin.macaroon ou /lnd/tls.cert)"
        echo "Vérifiez le montage du volume LND et les permissions (lecture requise)."
        exit 1
    fi
fi

# Configuration des dossiers
echo "Configuration des dossiers de données..."
mkdir -p ./data/metrics
mkdir -p ./data/raw
mkdir -p ./data/reports
mkdir -p ./data/actions
mkdir -p ./data/rollbacks
mkdir -p ./logs
mkdir -p ./rag/RAG_assets/logs
mkdir -p ./rag/RAG_assets/metrics
mkdir -p ./data/test

# Vérification des fichiers de configuration
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚠️ Fichier .env non trouvé, copie de .env.example..."
    cp .env.example .env
fi

# Activation du dry-run en fonction de l'environnement
if [ "$DRYRUN" = "true" ]; then
    echo "🔒 Mode DRYRUN activé - Aucune action réelle ne sera effectuée"
    export DRYRUN=true
else
    echo "⚠️ Mode DRYRUN désactivé - Les actions seront réellement exécutées"
    export DRYRUN=false
fi

# Désactiver DRYRUN en production pour l'API
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🚀 Mode production: DRYRUN désactivé pour l'API"
    export DRYRUN=false
fi

# Détermination de la commande à exécuter
if [ "$1" = "test" ]; then
    echo "Exécution des tests..."
    python3.9 -m pytest tests/ -v
elif [ "$1" = "rag" ]; then
    echo "Exécution du workflow RAG..."
    bash run_rag_workflow.sh
elif [ "$1" = "simulator" ]; then
    echo "Exécution du simulateur de nœud..."
    python3.9 src/tools/simulator/node_simulator.py
elif [ "$1" = "shell" ]; then
    echo "Démarrage du shell interactif..."
    exec /bin/bash
else
    # Démarrage de l'API par défaut
    echo "Démarrage de l'API MCP..."
    echo "=========================================="
    echo "L'API sera accessible sur le port 8000"
    echo "=========================================="
    # Try different app module paths
    if [ -f "app/main.py" ]; then
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
    elif [ -f "src/api/main.py" ]; then
        exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1
    elif [ -f "main.py" ]; then
        exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
    else
        echo "❌ Erreur: Impossible de trouver le module principal de l'API"
        echo "Tentative de démarrage avec le chemin par défaut..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
    fi
fi 