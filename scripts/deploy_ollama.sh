#!/bin/bash
# Script de déploiement Ollama pour MCP
# Usage: ./scripts/deploy_ollama.sh [dev|prod]

set -e

MODE="${1:-dev}"
COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}Déploiement Ollama/Llama 3 pour MCP${COLOR_RESET}"
echo -e "${COLOR_BLUE}Mode: ${MODE}${COLOR_RESET}"
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo ""

# Vérification préalable
if [ ! -f "docker-compose.production.yml" ]; then
    echo -e "${COLOR_RED}❌ Fichier docker-compose.production.yml non trouvé${COLOR_RESET}"
    exit 1
fi

if [ ! -f "scripts/ollama_init.sh" ]; then
    echo -e "${COLOR_RED}❌ Script ollama_init.sh non trouvé${COLOR_RESET}"
    exit 1
fi

# Vérifier le fichier .env
if [ ! -f ".env" ]; then
    echo -e "${COLOR_YELLOW}⚠️  Fichier .env non trouvé${COLOR_RESET}"
    if [ -f "env.ollama.example" ]; then
        echo -e "${COLOR_BLUE}Copie de env.ollama.example vers .env...${COLOR_RESET}"
        cp env.ollama.example .env
        echo -e "${COLOR_GREEN}✅ Fichier .env créé${COLOR_RESET}"
        echo -e "${COLOR_YELLOW}⚠️  IMPORTANT: Éditez .env avec vos valeurs avant de continuer!${COLOR_RESET}"
        read -p "Appuyez sur Entrée après avoir configuré .env..."
    else
        echo -e "${COLOR_RED}❌ Créez d'abord un fichier .env${COLOR_RESET}"
        exit 1
    fi
fi

# Étape 1: Arrêter les services existants
echo -e "${COLOR_YELLOW}[1/7] Arrêt des services existants...${COLOR_RESET}"
docker-compose -f docker-compose.production.yml down ollama mcp-api 2>/dev/null || true
echo -e "${COLOR_GREEN}✅ Services arrêtés${COLOR_RESET}"
echo ""

# Étape 2: Créer les volumes si nécessaire
echo -e "${COLOR_YELLOW}[2/7] Vérification des volumes...${COLOR_RESET}"
docker volume create mcp_ollama_data 2>/dev/null || echo "Volume ollama_data existe déjà"
docker volume create mcp_qdrant_data 2>/dev/null || echo "Volume qdrant_data existe déjà"
echo -e "${COLOR_GREEN}✅ Volumes vérifiés${COLOR_RESET}"
echo ""

# Étape 3: Démarrer Ollama
echo -e "${COLOR_YELLOW}[3/7] Démarrage du service Ollama...${COLOR_RESET}"
docker-compose -f docker-compose.production.yml up -d ollama
echo -e "${COLOR_GREEN}✅ Service Ollama démarré${COLOR_RESET}"
echo ""

# Étape 4: Attendre que Ollama soit prêt
echo -e "${COLOR_YELLOW}[4/7] Attente du healthcheck Ollama...${COLOR_RESET}"
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker exec mcp-ollama curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${COLOR_GREEN}✅ Ollama est prêt (${WAITED}s)${COLOR_RESET}"
        break
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "${COLOR_RED}❌ Timeout: Ollama ne répond pas après ${MAX_WAIT}s${COLOR_RESET}"
    echo "Vérifiez les logs: docker logs mcp-ollama"
    exit 1
fi
echo ""

# Étape 5: Initialiser les modèles
echo -e "${COLOR_YELLOW}[5/7] Initialisation des modèles Ollama...${COLOR_RESET}"

if [ "$MODE" == "dev" ]; then
    echo -e "${COLOR_BLUE}Mode développement: installation du modèle 8B uniquement${COLOR_RESET}"
    docker exec mcp-ollama ollama pull llama3:8b-instruct
    docker exec mcp-ollama ollama pull nomic-embed-text
    echo -e "${COLOR_GREEN}✅ Modèles dev installés (8B + embeddings)${COLOR_RESET}"
else
    echo -e "${COLOR_BLUE}Mode production: installation de tous les modèles (70B, 8B, embeddings)${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}⚠️  Cela peut prendre 1-3h selon votre connexion (45GB total)${COLOR_RESET}"
    read -p "Continuer? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker exec mcp-ollama /scripts/ollama_init.sh
        echo -e "${COLOR_GREEN}✅ Tous les modèles installés${COLOR_RESET}"
    else
        echo -e "${COLOR_YELLOW}Installation des modèles ignorée${COLOR_RESET}"
    fi
fi
echo ""

# Étape 6: Afficher les modèles installés
echo -e "${COLOR_YELLOW}[6/7] Modèles Ollama installés:${COLOR_RESET}"
docker exec mcp-ollama ollama list
echo ""

# Étape 7: Démarrer l'API MCP
echo -e "${COLOR_YELLOW}[7/7] Démarrage de l'API MCP...${COLOR_RESET}"
docker-compose -f docker-compose.production.yml up -d mcp-api
echo -e "${COLOR_GREEN}✅ API MCP démarrée${COLOR_RESET}"
echo ""

# Attendre un peu
echo -e "${COLOR_YELLOW}Attente du démarrage de l'API (10s)...${COLOR_RESET}"
sleep 10

# Tests de validation
echo ""
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}Tests de validation${COLOR_RESET}"
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo ""

# Test 1: Import du client
echo -e "${COLOR_YELLOW}Test 1: Import du client Ollama...${COLOR_RESET}"
if docker exec mcp-api python3 -c "from src.clients.ollama_client import ollama_client; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${COLOR_GREEN}✅ Client Ollama importé${COLOR_RESET}"
else
    echo -e "${COLOR_RED}❌ Erreur d'import du client${COLOR_RESET}"
fi

# Test 2: Import de l'adaptateur
echo -e "${COLOR_YELLOW}Test 2: Import de l'adaptateur RAG...${COLOR_RESET}"
if docker exec mcp-api python3 -c "from src.rag_ollama_adapter import OllamaRAGAdapter; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${COLOR_GREEN}✅ Adaptateur RAG importé${COLOR_RESET}"
else
    echo -e "${COLOR_RED}❌ Erreur d'import de l'adaptateur${COLOR_RESET}"
fi

# Test 3: Healthcheck Ollama depuis l'API
echo -e "${COLOR_YELLOW}Test 3: Healthcheck Ollama...${COLOR_RESET}"
HEALTH_CHECK=$(docker exec mcp-api python3 -c "
from src.clients.ollama_client import ollama_client
import asyncio
result = asyncio.run(ollama_client.healthcheck())
print('OK' if result else 'FAIL')
" 2>/dev/null || echo "FAIL")

if [ "$HEALTH_CHECK" == "OK" ]; then
    echo -e "${COLOR_GREEN}✅ Ollama accessible depuis l'API${COLOR_RESET}"
else
    echo -e "${COLOR_RED}❌ Ollama non accessible${COLOR_RESET}"
fi

# Résumé final
echo ""
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}✅ DÉPLOIEMENT TERMINÉ!${COLOR_RESET}"
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo ""
echo -e "${COLOR_BLUE}Services actifs:${COLOR_RESET}"
docker ps --filter name=mcp-ollama --filter name=mcp-api --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${COLOR_BLUE}Commandes utiles:${COLOR_RESET}"
echo "  Logs Ollama:     docker logs -f mcp-ollama"
echo "  Logs API:        docker logs -f mcp-api"
echo "  Stats:           docker stats mcp-ollama mcp-api"
echo "  Modèles:         docker exec mcp-ollama ollama list"
echo "  Validation:      ./scripts/validate_ollama_integration.sh"
echo ""
echo -e "${COLOR_BLUE}Documentation:${COLOR_RESET}"
echo "  Quick start:     QUICKSTART_OLLAMA.md"
echo "  Guide complet:   docs/OLLAMA_INTEGRATION_GUIDE.md"
echo ""
echo -e "${COLOR_GREEN}Prochaines étapes:${COLOR_RESET}"
echo "1. Vérifiez les logs: docker logs -f mcp-api"
echo "2. Testez un embedding: voir QUICKSTART_OLLAMA.md section 3"
echo "3. Exécutez les tests: pytest tests/unit/test_ollama_*.py -v"
echo "4. Consultez TODO_NEXT_OLLAMA.md pour la suite"
echo ""

