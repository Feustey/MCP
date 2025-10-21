#!/bin/bash
# scripts/pull_lightweight_models.sh
# Script pour télécharger les modèles légers Ollama pour production

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  MCP RAG - Récupération des Modèles Légers (Production) ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
OLLAMA_CONTAINER="mcp-ollama"
GEN_MODEL="llama3:8b-instruct"
FALLBACK_MODEL="phi3:medium"
EMBED_MODEL="nomic-embed-text"

# Vérifier si on est en Docker ou en local
if docker ps | grep -q "$OLLAMA_CONTAINER"; then
    echo -e "${GREEN}✓ Container Ollama détecté: $OLLAMA_CONTAINER${NC}"
    DOCKER_MODE=true
    OLLAMA_CMD="docker exec $OLLAMA_CONTAINER ollama"
else
    echo -e "${YELLOW}⚠ Container Ollama non trouvé, mode local${NC}"
    DOCKER_MODE=false
    OLLAMA_CMD="ollama"
    
    # Vérifier qu'Ollama est installé
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}❌ Ollama n'est pas installé${NC}"
        exit 1
    fi
fi

echo ""

# Fonction pour vérifier si un modèle existe
model_exists() {
    local model=$1
    if [ "$DOCKER_MODE" = true ]; then
        docker exec $OLLAMA_CONTAINER ollama list | grep -q "^$model"
    else
        ollama list | grep -q "^$model"
    fi
}

# Fonction pour pull un modèle
pull_model() {
    local model=$1
    local size=$2
    
    echo -e "${BLUE}📥 Téléchargement: ${model} (${size})${NC}"
    
    if model_exists "$model"; then
        echo -e "${YELLOW}⏭  Modèle déjà présent, skip${NC}"
        return 0
    fi
    
    if $OLLAMA_CMD pull "$model"; then
        echo -e "${GREEN}✅ ${model} téléchargé avec succès${NC}"
        return 0
    else
        echo -e "${RED}❌ Échec du téléchargement de ${model}${NC}"
        return 1
    fi
}

echo -e "${BLUE}Modèles à installer:${NC}"
echo "  1. ${GEN_MODEL} (~4.7 GB) - Génération principale"
echo "  2. ${FALLBACK_MODEL} (~4.0 GB) - Fallback"
echo "  3. ${EMBED_MODEL} (~274 MB) - Embeddings"
echo ""

# Pull des modèles
SUCCESS=0
TOTAL=3

echo -e "${BLUE}Début du téléchargement...${NC}"
echo ""

# Modèle principal
if pull_model "$GEN_MODEL" "~4.7 GB"; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""

# Modèle fallback
if pull_model "$FALLBACK_MODEL" "~4.0 GB"; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""

# Modèle embeddings
if pull_model "$EMBED_MODEL" "~274 MB"; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""

# Résumé
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    RÉSUMÉ                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $SUCCESS -eq $TOTAL ]; then
    echo -e "${GREEN}✅ Tous les modèles sont prêts ($SUCCESS/$TOTAL)${NC}"
else
    echo -e "${YELLOW}⚠ Téléchargement partiel ($SUCCESS/$TOTAL)${NC}"
fi

echo ""
echo -e "${BLUE}📊 Modèles disponibles:${NC}"
$OLLAMA_CMD list

# Test rapide du modèle principal
echo ""
echo -e "${BLUE}🔥 Test de warmup...${NC}"
if echo "Test. Réponds: OK" | $OLLAMA_CMD run "$GEN_MODEL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Modèle principal opérationnel${NC}"
else
    echo -e "${YELLOW}⚠ Test échoué (peut être normal au premier lancement)${NC}"
fi

echo ""
echo -e "${GREEN}✓ Setup terminé !${NC}"
echo ""
echo "Prochaines étapes:"
echo "  1. Vérifier .env avec GEN_MODEL=llama3:8b-instruct"
echo "  2. Lancer: docker-compose -f docker-compose.hostinger.yml up -d"
echo "  3. Tester le RAG workflow"
echo ""

