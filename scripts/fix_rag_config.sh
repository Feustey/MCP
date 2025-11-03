#!/bin/bash
# scripts/fix_rag_config.sh
# Correction de la configuration RAG

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Correction de la configuration RAG...${NC}"

# Vérifier que .env existe
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env non trouvé${NC}"
    echo "Copier env.hostinger.example vers .env et le configurer"
    exit 1
fi

# Sauvegarder l'ancien .env
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
echo -e "${YELLOW}📁 Sauvegarde créée: $BACKUP_FILE${NC}"

# Mettre à jour les variables RAG
echo -e "${YELLOW}📝 Mise à jour des variables RAG...${NC}"

# Créer un .env temporaire avec les bonnes valeurs
cat > .env.tmp << EOF
# Configuration RAG corrigée
ENABLE_RAG=true
OLLAMA_URL=http://ollama:11434
GEN_MODEL=llama3.2:3b
GEN_MODEL_FALLBACK=phi3:mini
EMBED_MODEL=nomic-embed-text
RAG_TIMEOUT=30
RAG_MAX_RETRIES=3
EOF

# Fusionner avec l'existant
grep -v -E "^(ENABLE_RAG|OLLAMA_URL|GEN_MODEL|GEN_MODEL_FALLBACK|EMBED_MODEL|RAG_TIMEOUT|RAG_MAX_RETRIES)=" .env > .env.new
cat .env.tmp >> .env.new
mv .env.new .env
rm .env.tmp

echo -e "${GREEN}✅ Configuration RAG mise à jour${NC}"

# Vérifier la configuration
echo -e "${YELLOW}🧪 Vérification de la configuration...${NC}"
if grep -q "GEN_MODEL=llama3.2:3b" .env; then
    echo -e "${GREEN}✅ GEN_MODEL configuré correctement${NC}"
else
    echo -e "${RED}❌ GEN_MODEL non configuré${NC}"
    exit 1
fi

if grep -q "ENABLE_RAG=true" .env; then
    echo -e "${GREEN}✅ ENABLE_RAG activé${NC}"
else
    echo -e "${RED}❌ ENABLE_RAG non activé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration RAG corrigée avec succès${NC}"
