#!/bin/bash
# deploy_rag_production.sh
# Déploiement complet du RAG avec modèles légers en production

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     MCP RAG - Déploiement Production (Modèles Légers)   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env non trouvé${NC}"
    echo "Copier env.hostinger.example vers .env et le configurer"
    exit 1
fi

# Vérifier GEN_MODEL dans .env
if ! grep -q "GEN_MODEL=llama3:8b-instruct" .env; then
    echo -e "${YELLOW}⚠ GEN_MODEL n'est pas configuré sur llama3:8b-instruct${NC}"
    echo "Voulez-vous continuer quand même? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓ Fichier .env trouvé${NC}"
echo ""

# Étape 1: Build et démarrage des services
echo -e "${BLUE}═══ ÉTAPE 1/5: Build et démarrage Docker ═══${NC}"
docker-compose -f docker-compose.hostinger.yml up -d --build

echo ""
echo -e "${YELLOW}⏳ Attente du démarrage des services (30s)...${NC}"
sleep 30

# Étape 2: Vérification de la santé des services
echo ""
echo -e "${BLUE}═══ ÉTAPE 2/5: Vérification santé des services ═══${NC}"

# MongoDB
if docker-compose -f docker-compose.hostinger.yml exec -T mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MongoDB: OK${NC}"
else
    echo -e "${RED}❌ MongoDB: ERREUR${NC}"
    exit 1
fi

# Redis
if docker-compose -f docker-compose.hostinger.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis: OK${NC}"
else
    echo -e "${RED}❌ Redis: ERREUR${NC}"
    exit 1
fi

# Ollama
if docker-compose -f docker-compose.hostinger.yml exec -T ollama curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama: OK${NC}"
else
    echo -e "${RED}❌ Ollama: ERREUR${NC}"
    exit 1
fi

# API
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP API: OK${NC}"
else
    echo -e "${YELLOW}⚠ MCP API: Pas encore prête (normal au premier lancement)${NC}"
fi

# Étape 3: Récupération des modèles
echo ""
echo -e "${BLUE}═══ ÉTAPE 3/5: Récupération des modèles Ollama ═══${NC}"
./scripts/pull_lightweight_models.sh

# Étape 4: Vérification des modèles
echo ""
echo -e "${BLUE}═══ ÉTAPE 4/5: Vérification des modèles ═══${NC}"
docker exec mcp-ollama ollama list

# Étape 5: Test du workflow RAG
echo ""
echo -e "${BLUE}═══ ÉTAPE 5/5: Test du workflow RAG ═══${NC}"
echo -e "${YELLOW}Lancement du workflow RAG...${NC}"

if ./run_rag_workflow_prod.sh; then
    echo -e "${GREEN}✅ Workflow RAG exécuté avec succès${NC}"
else
    echo -e "${YELLOW}⚠ Workflow RAG avec warnings (vérifier les logs)${NC}"
fi

# Résumé final
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              DÉPLOIEMENT TERMINÉ !                       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Services actifs:${NC}"
docker-compose -f docker-compose.hostinger.yml ps

echo ""
echo -e "${BLUE}Accès aux services:${NC}"
echo "  • API MCP: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Grafana: http://localhost:3000"
echo "  • Prometheus: http://localhost:9090"
echo ""

echo -e "${BLUE}Commandes utiles:${NC}"
echo "  • Logs API: docker-compose -f docker-compose.hostinger.yml logs -f mcp-api"
echo "  • Logs Ollama: docker-compose -f docker-compose.hostinger.yml logs -f ollama"
echo "  • Arrêter: docker-compose -f docker-compose.hostinger.yml down"
echo "  • RAG workflow: ./run_rag_workflow_prod.sh"
echo ""

echo -e "${GREEN}✓ Déploiement RAG Production réussi !${NC}"

