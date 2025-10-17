#!/bin/bash

# Script pour télécharger et configurer les modèles Ollama optimaux pour MCP
# Usage: ./scripts/setup_ollama_models.sh [profile]
# Profiles: minimal, recommended, full

set -e

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    MCP Ollama Models Setup - Lightning Optimizer        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier qu'Ollama est installé
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama n'est pas installé${NC}"
    echo ""
    echo "Installation:"
    echo "  macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  Windows: https://ollama.com/download"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Ollama est installé${NC}"
echo ""

# Vérifier qu'Ollama est lancé
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama n'est pas lancé${NC}"
    echo "Démarrage d'Ollama..."
    ollama serve &
    sleep 3
fi

# Déterminer le profil
PROFILE=${1:-recommended}

echo -e "${BLUE}Profil sélectionné: ${PROFILE}${NC}"
echo ""

# Définir les modèles selon le profil
case $PROFILE in
    minimal)
        echo "Profil MINIMAL: Modèles légers pour RAM limitée (< 16GB)"
        MODELS=(
            "llama3:8b-instruct"
            "phi3:medium"
        )
        ;;
    
    recommended)
        echo "Profil RECOMMANDÉ: Balance performance/qualité (16-32GB RAM)"
        MODELS=(
            "llama3:8b-instruct"
            "phi3:medium"
            "qwen2.5:14b-instruct"
            "codellama:13b-instruct"
        )
        ;;
    
    full)
        echo "Profil FULL: Tous les modèles optimisés (32GB+ RAM)"
        MODELS=(
            "llama3:8b-instruct"
            "llama3:13b-instruct"
            "phi3:medium"
            "qwen2.5:14b-instruct"
            "codellama:13b-instruct"
            "mistral:7b-instruct"
        )
        ;;
    
    *)
        echo -e "${RED}Profil inconnu: $PROFILE${NC}"
        echo "Profils disponibles: minimal, recommended, full"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Modèles à télécharger: ${#MODELS[@]}${NC}"
for model in "${MODELS[@]}"; do
    echo "  - $model"
done
echo ""

# Fonction pour télécharger un modèle
download_model() {
    local model=$1
    echo -e "${BLUE}📥 Téléchargement de ${model}...${NC}"
    
    if ollama pull $model; then
        echo -e "${GREEN}✓ ${model} téléchargé avec succès${NC}"
        return 0
    else
        echo -e "${RED}✗ Échec du téléchargement de ${model}${NC}"
        return 1
    fi
}

# Télécharger chaque modèle
SUCCESS_COUNT=0
FAIL_COUNT=0

for model in "${MODELS[@]}"; do
    # Vérifier si déjà téléchargé
    if ollama list | grep -q "^$model"; then
        echo -e "${YELLOW}⏭  ${model} déjà présent, skip${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        if download_model $model; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    fi
    echo ""
done

# Résumé
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    RÉSUMÉ                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Succès: ${SUCCESS_COUNT}/${#MODELS[@]}${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}✗ Échecs: ${FAIL_COUNT}/${#MODELS[@]}${NC}"
fi
echo ""

# Lister les modèles disponibles
echo -e "${BLUE}Modèles Ollama installés:${NC}"
ollama list
echo ""

# Test rapide
echo -e "${BLUE}Test rapide du modèle principal...${NC}"
if echo "Résume Lightning Network en 2 phrases" | ollama run llama3:8b-instruct > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Modèle principal opérationnel${NC}"
else
    echo -e "${YELLOW}⚠️  Test échoué, mais modèles installés${NC}"
fi
echo ""

# Recommandations
echo -e "${BLUE}Prochaines étapes:${NC}"
echo ""
echo "1. Tester un modèle:"
echo "   ollama run llama3:8b-instruct"
echo ""
echo "2. Vérifier la configuration MCP:"
echo "   cat .env | grep -E '(EMBED_MODEL|GEN_MODEL)'"
echo ""
echo "3. Lancer l'API MCP:"
echo "   uvicorn main:app --reload"
echo ""
echo "4. Tester les recommandations optimisées:"
echo "   python scripts/test_ollama_recommendations.py"
echo ""

# Configuration recommandée .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé${NC}"
    echo ""
    echo "Configuration recommandée pour .env:"
    echo ""
    cat << EOF
# Ollama Models Configuration
EMBED_MODEL=nomic-embed-text
GEN_MODEL=qwen2.5:14b-instruct
GEN_MODEL_FALLBACK=llama3:8b-instruct

# Ollama Parameters
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=90

# RAG Configuration
RAG_TOPK=5
RAG_TEMPERATURE=0.3
RAG_MAX_TOKENS=2500
EOF
    echo ""
fi

echo -e "${GREEN}✓ Setup Ollama terminé !${NC}"
echo ""

