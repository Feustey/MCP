#!/bin/bash
# Vérification rapide que tous les fichiers v2.0 sont présents

echo "🔍 Vérification des fichiers MCP v2.0"
echo "======================================"
echo ""

files=(
    "app/services/rag_metrics.py"
    "src/utils/circuit_breaker.py"
    "src/rag_batch_optimizer.py"
    "src/vector_index_faiss.py"
    "src/intelligent_model_router.py"
    "app/routes/streaming.py"
    "app/services/recommendation_scorer.py"
    "app/services/recommendation_feedback.py"
    "src/ollama_strategy_optimizer.py"
    "src/ollama_rag_optimizer.py"
    "prompts/lightning_recommendations_v2.md"
    "scripts/cache_warmer.py"
    "scripts/setup_ollama_models.sh"
    "scripts/test_ollama_recommendations.py"
    "scripts/validate_all_optimizations.py"
    "START_HERE_V2.md"
    "QUICKSTART_V2.md"
    "MCP_V2_COMPLETE_SUMMARY.md"
    "OLLAMA_OPTIMIZATION_COMPLETE.md"
    "OLLAMA_INTEGRATION_GUIDE.md"
    "FINAL_VALIDATION_INSTRUCTIONS.md"
    "INDEX_V2_COMPLETE.md"
    "README_MCP_V2.md"
    "CHANGELOG_V2.md"
    "TLDR_V2.md"
)

present=0
missing=0

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
        present=$((present + 1))
    else
        echo "✗ $file (MANQUANT)"
        missing=$((missing + 1))
    fi
done

echo ""
echo "======================================"
echo "Résultat: $present présents, $missing manquants"

if [ $missing -eq 0 ]; then
    echo "✅ TOUS LES FICHIERS PRÉSENTS !"
    exit 0
else
    echo "⚠️  Certains fichiers manquent"
    exit 1
fi
