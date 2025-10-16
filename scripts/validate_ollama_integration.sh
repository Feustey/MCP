#!/bin/bash
# Script de validation de l'intégration Ollama
# Usage: ./scripts/validate_ollama_integration.sh

set -e

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RESET='\033[0m'

echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}Validation intégration Ollama/Llama 3${COLOR_RESET}"
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
echo ""

ERRORS=0

# Fonction pour afficher les résultats
check() {
    if [ $? -eq 0 ]; then
        echo -e "${COLOR_GREEN}✅ $1${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}❌ $1${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
}

# 1. Vérification des fichiers
echo -e "${COLOR_YELLOW}[1/8] Vérification des fichiers...${COLOR_RESET}"
test -f src/clients/ollama_client.py
check "Client Ollama existe"

test -f src/rag_ollama_adapter.py
check "Adaptateur RAG existe"

test -f scripts/ollama_init.sh
check "Script d'initialisation existe"

test -f tests/unit/test_ollama_client.py
check "Tests client existent"

test -f tests/unit/test_rag_ollama_adapter.py
check "Tests adaptateur existent"

test -f docs/OLLAMA_INTEGRATION_GUIDE.md
check "Guide d'intégration existe"

# 2. Vérification de la configuration
echo ""
echo -e "${COLOR_YELLOW}[2/8] Vérification de la configuration...${COLOR_RESET}"

if [ -f .env ]; then
    if grep -q "LLM_PROVIDER" .env; then
        check "Variable LLM_PROVIDER présente dans .env"
    else
        echo -e "${COLOR_RED}❌ Variable LLM_PROVIDER manquante dans .env${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
    
    if grep -q "OLLAMA_URL" .env; then
        check "Variable OLLAMA_URL présente dans .env"
    else
        echo -e "${COLOR_RED}❌ Variable OLLAMA_URL manquante dans .env${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${COLOR_YELLOW}⚠️  Fichier .env non trouvé (créer depuis env.example)${COLOR_RESET}"
fi

# 3. Vérification du docker-compose
echo ""
echo -e "${COLOR_YELLOW}[3/8] Vérification Docker Compose...${COLOR_RESET}"

if grep -q "ollama:" docker-compose.production.yml; then
    check "Service Ollama défini dans docker-compose"
else
    echo -e "${COLOR_RED}❌ Service Ollama manquant dans docker-compose${COLOR_RESET}"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "ollama_data:" docker-compose.production.yml; then
    check "Volume ollama_data défini"
else
    echo -e "${COLOR_RED}❌ Volume ollama_data manquant${COLOR_RESET}"
    ERRORS=$((ERRORS + 1))
fi

# 4. Vérification de la syntaxe Python
echo ""
echo -e "${COLOR_YELLOW}[4/8] Vérification syntaxe Python...${COLOR_RESET}"

python3 -m py_compile src/clients/ollama_client.py 2>/dev/null
check "Client Ollama: syntaxe valide"

python3 -m py_compile src/rag_ollama_adapter.py 2>/dev/null
check "Adaptateur RAG: syntaxe valide"

python3 -m py_compile config/rag_config.py 2>/dev/null
check "Configuration RAG: syntaxe valide"

# 5. Tests unitaires
echo ""
echo -e "${COLOR_YELLOW}[5/8] Exécution des tests unitaires...${COLOR_RESET}"

if command -v pytest &> /dev/null; then
    pytest tests/unit/test_ollama_client.py -v --tb=short > /tmp/test_ollama_client.log 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${COLOR_GREEN}✅ Tests client Ollama (15 tests)${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}❌ Tests client Ollama échoués${COLOR_RESET}"
        echo "Voir /tmp/test_ollama_client.log pour détails"
        ERRORS=$((ERRORS + 1))
    fi
    
    pytest tests/unit/test_rag_ollama_adapter.py -v --tb=short > /tmp/test_rag_adapter.log 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${COLOR_GREEN}✅ Tests adaptateur RAG (14 tests)${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}❌ Tests adaptateur RAG échoués${COLOR_RESET}"
        echo "Voir /tmp/test_rag_adapter.log pour détails"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${COLOR_YELLOW}⚠️  pytest non installé, tests unitaires ignorés${COLOR_RESET}"
fi

# 6. Vérification service Docker Ollama (si running)
echo ""
echo -e "${COLOR_YELLOW}[6/8] Vérification service Ollama...${COLOR_RESET}"

if docker ps | grep -q "mcp-ollama"; then
    echo -e "${COLOR_GREEN}✅ Service Ollama en cours d'exécution${COLOR_RESET}"
    
    # Test healthcheck
    if docker exec mcp-ollama curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        check "Healthcheck Ollama OK"
    else
        echo -e "${COLOR_RED}❌ Healthcheck Ollama échoué${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
    
    # Liste des modèles
    echo -e "${COLOR_BLUE}Modèles installés:${COLOR_RESET}"
    docker exec mcp-ollama ollama list || echo "Impossible de lister les modèles"
else
    echo -e "${COLOR_YELLOW}⚠️  Service Ollama non démarré (docker-compose up -d ollama)${COLOR_RESET}"
fi

# 7. Vérification service MCP API (si running)
echo ""
echo -e "${COLOR_YELLOW}[7/8] Vérification service MCP API...${COLOR_RESET}"

if docker ps | grep -q "mcp-api"; then
    echo -e "${COLOR_GREEN}✅ Service MCP API en cours d'exécution${COLOR_RESET}"
    
    # Vérifier les imports
    if docker exec mcp-api python3 -c "from src.clients.ollama_client import ollama_client; print('OK')" 2>/dev/null | grep -q "OK"; then
        check "Import client Ollama OK"
    else
        echo -e "${COLOR_RED}❌ Impossible d'importer le client Ollama${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
    
    if docker exec mcp-api python3 -c "from src.rag_ollama_adapter import OllamaRAGAdapter; print('OK')" 2>/dev/null | grep -q "OK"; then
        check "Import adaptateur RAG OK"
    else
        echo -e "${COLOR_RED}❌ Impossible d'importer l'adaptateur RAG${COLOR_RESET}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${COLOR_YELLOW}⚠️  Service MCP API non démarré (docker-compose up -d mcp-api)${COLOR_RESET}"
fi

# 8. Documentation
echo ""
echo -e "${COLOR_YELLOW}[8/8] Vérification documentation...${COLOR_RESET}"

test -f docs/OLLAMA_INTEGRATION_GUIDE.md
check "Guide d'intégration"

test -f OLLAMA_INTEGRATION_COMPLETE.md
check "Résumé d'intégration"

test -f QUICKSTART_OLLAMA.md
check "Quick start"

test -f TODO_NEXT_OLLAMA.md
check "TODO next steps"

# Résumé final
echo ""
echo -e "${COLOR_BLUE}========================================${COLOR_RESET}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${COLOR_GREEN}✅ VALIDATION RÉUSSIE!${COLOR_RESET}"
    echo -e "${COLOR_GREEN}L'intégration Ollama est prête.${COLOR_RESET}"
    echo ""
    echo -e "${COLOR_BLUE}Prochaines étapes:${COLOR_RESET}"
    echo "1. Démarrer Ollama: docker-compose up -d ollama"
    echo "2. Initialiser modèles: docker exec mcp-ollama /scripts/ollama_init.sh"
    echo "3. Démarrer API: docker-compose up -d mcp-api"
    echo "4. Voir: QUICKSTART_OLLAMA.md"
    exit 0
else
    echo -e "${COLOR_RED}❌ VALIDATION ÉCHOUÉE (${ERRORS} erreur(s))${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}Corrigez les erreurs ci-dessus avant de continuer.${COLOR_RESET}"
    exit 1
fi

