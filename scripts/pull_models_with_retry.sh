#!/bin/bash
# scripts/pull_models_with_retry.sh
# Téléchargement des modèles Ollama avec retry et modèles plus légers

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MAX_RETRIES=3
TIMEOUT=300
DELAY=30

# Modèles à télécharger (plus légers)
MODELS=(
    "llama3.2:3b"
    "phi3:mini"
    "nomic-embed-text"
)

echo -e "${BLUE}🤖 Téléchargement des modèles Ollama avec retry...${NC}"

# Vérifier que le conteneur Ollama est en cours d'exécution
if ! docker ps | grep -q "mcp-ollama"; then
    echo -e "${RED}❌ Conteneur Ollama non trouvé${NC}"
    exit 1
fi

pull_with_retry() {
    local model=$1
    local retry=0
    
    echo -e "${BLUE}📥 Téléchargement: $model${NC}"
    
    # Vérifier si le modèle existe déjà
    if docker exec mcp-ollama ollama list | grep -q "^$model"; then
        echo -e "${YELLOW}  ⏭️ Modèle déjà présent, skip${NC}"
        return 0
    fi
    
    while [ $retry -lt $MAX_RETRIES ]; do
        echo -e "${YELLOW}  Tentative $((retry + 1))/$MAX_RETRIES${NC}"
        
        if timeout $TIMEOUT docker exec mcp-ollama ollama pull "$model" 2>/dev/null; then
            echo -e "${GREEN}  ✅ $model téléchargé avec succès${NC}"
            return 0
        fi
        
        echo -e "${RED}  ❌ Échec, retry dans ${DELAY}s...${NC}"
        sleep $DELAY
        retry=$((retry + 1))
    done
    
    echo -e "${RED}  ❌ Échec définitif pour $model${NC}"
    return 1
}

SUCCESS=0
TOTAL=${#MODELS[@]}

for model in "${MODELS[@]}"; do
    if pull_with_retry "$model"; then
        SUCCESS=$((SUCCESS + 1))
    fi
    echo ""
done

echo -e "${BLUE}📊 Résumé: $SUCCESS/$TOTAL modèles téléchargés${NC}"

if [ $SUCCESS -eq $TOTAL ]; then
    echo -e "${GREEN}✅ Tous les modèles sont prêts${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️ Téléchargement partiel${NC}"
    exit 1
fi
