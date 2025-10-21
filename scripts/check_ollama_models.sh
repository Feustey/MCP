#!/bin/bash
# Script de vérification et validation des modèles Ollama
# Date: 20 octobre 2025
#
# Vérifie les modèles disponibles et propose des alternatives selon l'espace disque

set -e

echo "🤖 Vérification des Modèles Ollama pour MCP"
echo "==========================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container Ollama
OLLAMA_CONTAINER=${OLLAMA_CONTAINER:-mcp-ollama}

# Vérifier si Ollama est accessible
echo "📋 Vérification du service Ollama..."
if ! docker ps | grep -q "$OLLAMA_CONTAINER"; then
    echo -e "${RED}❌ Container Ollama non actif${NC}"
    echo "Démarrer avec: docker-compose up -d ollama"
    exit 1
fi

if ! docker exec "$OLLAMA_CONTAINER" ollama list > /dev/null 2>&1; then
    echo -e "${RED}❌ Service Ollama non accessible${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Service Ollama accessible${NC}"
echo ""

# Lister les modèles disponibles
echo "📦 Modèles actuellement disponibles:"
echo "-----------------------------------"
docker exec "$OLLAMA_CONTAINER" ollama list
echo ""

# Vérifier l'espace disque disponible
echo "💾 Espace disque disponible:"
echo "----------------------------"
AVAILABLE_GB=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
echo "Disponible: ${AVAILABLE_GB}GB"
echo ""

# Modèles requis selon la configuration
declare -A REQUIRED_MODELS=(
    ["llama3.1:8b"]="4.7"
    ["llama3:8b-instruct"]="4.7"
    ["phi3:medium"]="4.0"
    ["nomic-embed-text"]="0.3"
)

declare -A ALTERNATIVE_MODELS=(
    ["llama3.2:3b"]="2.0"
    ["phi3:mini"]="2.0"
    ["tinyllama"]="0.6"
)

# Vérifier quels modèles sont disponibles
echo "🔍 Analyse des modèles requis:"
echo "-----------------------------"

AVAILABLE_MODELS=$(docker exec "$OLLAMA_CONTAINER" ollama list | tail -n +2 | awk '{print $1}')
MISSING_MODELS=()
TOTAL_REQUIRED_SIZE=0

for model in "${!REQUIRED_MODELS[@]}"; do
    size=${REQUIRED_MODELS[$model]}
    if echo "$AVAILABLE_MODELS" | grep -q "$model"; then
        echo -e "${GREEN}✅ $model (${size}GB)${NC}"
    else
        echo -e "${RED}❌ $model (${size}GB) - MANQUANT${NC}"
        MISSING_MODELS+=("$model")
        TOTAL_REQUIRED_SIZE=$(echo "$TOTAL_REQUIRED_SIZE + $size" | bc)
    fi
done
echo ""

# Vérifier si on a assez d'espace pour les modèles manquants
if [ ${#MISSING_MODELS[@]} -gt 0 ]; then
    echo "⚠️  Modèles manquants: ${#MISSING_MODELS[@]}"
    echo "Espace requis: ${TOTAL_REQUIRED_SIZE}GB"
    echo "Espace disponible: ${AVAILABLE_GB}GB"
    echo ""
    
    if (( $(echo "$AVAILABLE_GB > ($TOTAL_REQUIRED_SIZE + 5)" | bc -l) )); then
        echo -e "${GREEN}✅ Espace suffisant pour télécharger les modèles manquants${NC}"
        echo ""
        
        read -p "Voulez-vous télécharger les modèles manquants maintenant? (o/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Oo]$ ]]; then
            for model in "${MISSING_MODELS[@]}"; do
                echo ""
                echo "📥 Téléchargement de $model..."
                docker exec "$OLLAMA_CONTAINER" ollama pull "$model" || {
                    echo -e "${RED}❌ Échec du téléchargement de $model${NC}"
                    echo "Vérifier la connectivité réseau"
                }
            done
            echo ""
            echo "📦 Modèles après téléchargement:"
            docker exec "$OLLAMA_CONTAINER" ollama list
        fi
    else
        echo -e "${RED}❌ Espace insuffisant (manque: $(echo "$TOTAL_REQUIRED_SIZE + 5 - $AVAILABLE_GB" | bc)GB)${NC}"
        echo ""
        echo "💡 Alternatives recommandées (modèles plus légers):"
        echo "---------------------------------------------------"
        
        TOTAL_ALT_SIZE=0
        for model in "${!ALTERNATIVE_MODELS[@]}"; do
            size=${ALTERNATIVE_MODELS[$model]}
            echo "  • $model (${size}GB)"
            TOTAL_ALT_SIZE=$(echo "$TOTAL_ALT_SIZE + $size" | bc)
        done
        echo ""
        echo "Espace requis pour alternatives: ${TOTAL_ALT_SIZE}GB"
        
        if (( $(echo "$AVAILABLE_GB > ($TOTAL_ALT_SIZE + 3)" | bc -l) )); then
            echo -e "${GREEN}✅ Espace suffisant pour les alternatives${NC}"
            echo ""
            
            read -p "Voulez-vous télécharger les modèles alternatifs? (o/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Oo]$ ]]; then
                for model in "${!ALTERNATIVE_MODELS[@]}"; do
                    echo ""
                    echo "📥 Téléchargement de $model..."
                    docker exec "$OLLAMA_CONTAINER" ollama pull "$model" || {
                        echo -e "${RED}❌ Échec du téléchargement de $model${NC}"
                    }
                done
                
                echo ""
                echo "⚙️  Mettre à jour la configuration .env avec:"
                echo "-------------------------------------------"
                echo "GEN_MODEL=llama3.2:3b"
                echo "GEN_MODEL_FALLBACK=phi3:mini"
                echo "EMBED_MODEL=nomic-embed-text"
            fi
        else
            echo -e "${RED}❌ Espace insuffisant même pour les alternatives${NC}"
            echo ""
            echo "💡 Mode dégradé recommandé:"
            echo "--------------------------"
            echo "  • Utiliser seulement nomic-embed-text (0.3GB)"
            echo "  • Désactiver la génération de texte"
            echo ""
            echo "Configuration .env:"
            echo "  GEN_MODEL=nomic-embed-text"
            echo "  GEN_MODEL_FALLBACK=nomic-embed-text"
            echo "  ENABLE_RAG=false"
        fi
    fi
else
    echo -e "${GREEN}✅ Tous les modèles requis sont disponibles${NC}"
fi

echo ""
echo "==========================================="
echo "🎯 Recommandations:"
echo "-------------------"

# Compter les modèles disponibles
MODEL_COUNT=$(echo "$AVAILABLE_MODELS" | wc -l)

if [ "$MODEL_COUNT" -ge 3 ]; then
    echo -e "${GREEN}✅ Configuration optimale${NC}"
    echo "  • Génération de texte: Activée"
    echo "  • Embeddings: Activés"
    echo "  • RAG: Pleinement fonctionnel"
elif [ "$MODEL_COUNT" -ge 1 ]; then
    echo -e "${YELLOW}⚠️  Configuration limitée${NC}"
    echo "  • Vérifier quelle fonctionnalité est disponible"
    echo "  • Télécharger les modèles manquants si possible"
else
    echo -e "${RED}❌ Configuration insuffisante${NC}"
    echo "  • Télécharger au minimum nomic-embed-text"
    echo "  • Vérifier la connectivité réseau"
fi

echo ""
echo "📝 Logs et troubleshooting:"
echo "  docker logs $OLLAMA_CONTAINER"
echo "  docker exec $OLLAMA_CONTAINER ollama list"
echo "  docker exec $OLLAMA_CONTAINER ollama pull <model_name>"
echo ""

