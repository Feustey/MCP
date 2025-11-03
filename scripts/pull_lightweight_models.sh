#!/bin/bash
# scripts/pull_lightweight_models.sh
# Téléchargement des modèles ultra-légers pour 2GB RAM

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        TÉLÉCHARGEMENT MODÈLES ULTRA-LÉGERS              ║${NC}"
echo -e "${BLUE}║              Compatibles 2GB RAM                        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier que Docker est en cours d'exécution
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker n'est pas en cours d'exécution${NC}"
    exit 1
fi

# Vérifier que le conteneur Ollama est en cours d'exécution
if ! docker ps | grep -q "mcp-ollama"; then
    echo -e "${RED}❌ Conteneur Ollama non trouvé${NC}"
    exit 1
fi

# Modèles ultra-légers recommandés pour 2GB RAM
MODELS=(
    "gemma3:1b"      # ~1GB RAM - Recommandé
    "tinyllama"      # ~500MB RAM - Très léger
    "qwen2.5:1.5b"   # ~1.5GB RAM - Alternative
)

echo -e "${YELLOW}🤖 Téléchargement des modèles ultra-légers pour 2GB RAM...${NC}"
echo ""

SUCCESS=0
TOTAL=${#MODELS[@]}

for model in "${MODELS[@]}"; do
    echo -e "${BLUE}📥 Téléchargement: $model${NC}"
    
    if docker exec mcp-ollama ollama pull "$model"; then
        echo -e "${GREEN}✅ $model téléchargé avec succès${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}❌ Échec pour $model${NC}"
    fi
    echo ""
done

echo -e "${BLUE}📊 Résumé: $SUCCESS/$TOTAL modèles téléchargés${NC}"

if [ $SUCCESS -gt 0 ]; then
    echo -e "${GREEN}✅ Au moins un modèle ultra-léger est disponible${NC}"
    echo ""
    echo -e "${YELLOW}💡 Prochaines étapes:${NC}"
    echo "  1. Mettre à jour la configuration RAG"
    echo "  2. Redémarrer l'API"
    echo "  3. Tester l'endpoint RAG"
    exit 0
else
    echo -e "${RED}❌ Aucun modèle n'a pu être téléchargé${NC}"
    exit 1
fi