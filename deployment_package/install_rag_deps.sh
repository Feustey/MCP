#!/bin/sh

# Script d'installation des dépendances RAG
# Dernière mise à jour: 9 mai 2025

echo "🔧 Installation des dépendances RAG..."

# Vérification de Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 n'est pas installé"
    exit 1
fi

# Installation des dépendances de base d'abord
echo "📦 Installation des dépendances de base..."
pip install -r requirements-hostinger.txt

# Installation des dépendances RAG avec gestion d'erreurs
echo "🤖 Installation des dépendances RAG..."
if [ -f "requirements-rag.txt" ]; then
    # Tentative d'installation avec gestion d'erreurs
    pip install sentence-transformers transformers torch --no-deps || {
        echo "⚠️ Installation des dépendances RAG échouée, utilisation du mode sans RAG"
        echo "ℹ️ Les fonctionnalités RAG ne seront pas disponibles"
    }
else
    echo "❌ Fichier requirements-rag.txt non trouvé"
    exit 1
fi

echo "✅ Installation terminée"
echo "ℹ️ Pour vérifier l'installation: python3 -c 'import sentence_transformers; print(\"✅ RAG disponible\")'" 