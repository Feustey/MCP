#!/bin/bash
# Script d'initialisation Ollama - Pull des modèles requis
# Usage: docker exec mcp-ollama /scripts/ollama_init.sh

set -e

echo "==================================="
echo "Initialisation des modèles Ollama"
echo "==================================="

# Fonction pour vérifier si un modèle existe
model_exists() {
    ollama list | grep -q "$1"
}

# Modèles requis
GEN_MODEL="${GEN_MODEL:-llama3:70b-instruct-2025-07-01}"
FALLBACK_MODEL="${FALLBACK_MODEL:-llama3:8b-instruct}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

echo ""
echo "📦 Modèles à installer:"
echo "  - Génération principale: $GEN_MODEL"
echo "  - Génération fallback: $FALLBACK_MODEL"
echo "  - Embeddings: $EMBED_MODEL"
echo ""

# Pull modèle de génération principal (70B)
if model_exists "$GEN_MODEL"; then
    echo "✅ $GEN_MODEL déjà présent"
else
    echo "⏳ Téléchargement de $GEN_MODEL (cela peut prendre du temps, ~40GB)..."
    ollama pull "$GEN_MODEL"
    echo "✅ $GEN_MODEL installé"
fi

# Pull modèle fallback (8B)
if model_exists "$FALLBACK_MODEL"; then
    echo "✅ $FALLBACK_MODEL déjà présent"
else
    echo "⏳ Téléchargement de $FALLBACK_MODEL (~4.7GB)..."
    ollama pull "$FALLBACK_MODEL"
    echo "✅ $FALLBACK_MODEL installé"
fi

# Pull modèle d'embeddings
if model_exists "$EMBED_MODEL"; then
    echo "✅ $EMBED_MODEL déjà présent"
else
    echo "⏳ Téléchargement de $EMBED_MODEL (~274MB)..."
    ollama pull "$EMBED_MODEL"
    echo "✅ $EMBED_MODEL installé"
fi

echo ""
echo "==================================="
echo "✅ Tous les modèles sont prêts!"
echo "==================================="
echo ""
echo "📊 Modèles disponibles:"
ollama list

echo ""
echo "🔥 Test de warmup du modèle principal..."
echo "Ceci charge le modèle en mémoire pour des réponses plus rapides."
ollama run "$GEN_MODEL" "Test warmup. Réponds simplement: OK" --verbose=false

echo ""
echo "✅ Initialisation terminée avec succès!"

