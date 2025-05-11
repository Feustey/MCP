#!/bin/bash

# Script de lancement MCP avec configuration apple
# Ce script démarre tous les composants nécessaires de MCP

# Définir le chemin absolu du projet
PROJECT_PATH="/Users/stephanecourant/Documents/DAZ/MCP/MCP"

# Se déplacer vers le répertoire du projet
cd "$PROJECT_PATH"

# Styles de texte pour un meilleur affichage
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}⚡ Préparation de l'environnement MCP...${NC}"

# Copier .env.apple vers .env
cp .env.apple .env && echo -e "${GREEN}✅ Fichier .env.apple chargé${NC}"

# Vérifier MongoDB
echo -e "${BLUE}🔍 Vérification de MongoDB...${NC}"
if ! mongod --version >/dev/null 2>&1; then
    echo -e "${RED}❌ MongoDB n'est pas installé${NC}"
    exit 1
fi

if ! mongo --eval "db.serverStatus()" >/dev/null 2>&1; then
    echo -e "${YELLOW}🚀 Démarrage de MongoDB...${NC}"
    mongod --fork --logpath /tmp/mongodb.log
fi

# Vérifier Redis
echo -e "${BLUE}🔍 Vérification de Redis...${NC}"
if ! redis-cli ping >/dev/null 2>&1; then
    echo -e "${YELLOW}🚀 Démarrage de Redis...${NC}"
    redis-server --daemonize yes
fi

# Activer l'environnement virtuel
echo -e "${BLUE}🐍 Activation de l'environnement virtuel...${NC}"
source venv/bin/activate

# Créer les tmux sessions
if command -v tmux &> /dev/null; then
    # S'assurer qu'aucune session nommée MCP n'existe déjà
    tmux kill-session -t MCP 2>/dev/null
    
    # Créer une nouvelle session
    tmux new-session -d -s MCP -n "Contrôle"
    
    # Fenêtre 1: Contrôle - Déjà créée
    tmux send-keys -t MCP:0 "cd \"$PROJECT_PATH\" && source venv/bin/activate" C-m
    tmux send-keys -t MCP:0 "echo -e \"${GREEN}✅ MCP est prêt à être lancé!${NC}\"" C-m
    
    # Fenêtre 2: Serveur API
    tmux new-window -t MCP:1 -n "API"
    tmux send-keys -t MCP:1 "cd \"$PROJECT_PATH\" && source venv/bin/activate" C-m
    tmux send-keys -t MCP:1 "echo -e \"${YELLOW}🚀 Démarrage du serveur API...${NC}\"" C-m
    tmux send-keys -t MCP:1 "python server.py" C-m
    
    # Fenêtre 3: Collecte de données
    tmux new-window -t MCP:2 -n "Collecte"
    tmux send-keys -t MCP:2 "cd \"$PROJECT_PATH\" && source venv/bin/activate" C-m
    tmux send-keys -t MCP:2 "echo -e \"${YELLOW}📊 Démarrage du système de collecte de données...${NC}\"" C-m
    tmux send-keys -t MCP:2 "python run_test_system.py" C-m
    
    # Fenêtre 4: Console interactive
    tmux new-window -t MCP:3 -n "Console"
    tmux send-keys -t MCP:3 "cd \"$PROJECT_PATH\" && source venv/bin/activate" C-m
    tmux send-keys -t MCP:3 "echo -e \"${BLUE}🎮 Console MCP active - Commandes utiles:${NC}\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\n📝 Interrogation RAG:\npython lnbits_rag_integration.py --query \\\"Comment optimiser mon nœud lightning?\\\"\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\n📊 Analyse d'un nœud:\npython amboss_scraper.py --node-id <pubkey>\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\n💰 Recharger le wallet:\npython topup_wallet.py 9000000\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\n🧪 Tests:\npython test_lnbits_connection.py\npython test_health.py\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\n⚙️ Optimisation:\npython optimize_feustey_config.py\"" C-m
    tmux send-keys -t MCP:3 "echo -e \"\nPour arrêter tous les processus:\npkill -f \\\"python.*run_test_system\\\"\npkill -f \\\"python.*server\\\"\"" C-m
    
    # Test de connexion à LNBits dans la première fenêtre
    tmux select-window -t MCP:0
    tmux send-keys -t MCP:0 "echo -e \"${BLUE}🔍 Test de la connexion LNBits...${NC}\"" C-m
    tmux send-keys -t MCP:0 "python test_lnbits_connection.py || echo -e \"${YELLOW}⚠️ Avertissement: La connexion LNBits a échoué${NC}\"" C-m
    
    echo -e "${GREEN}✅ MCP est lancé dans tmux!${NC}"
    echo -e "${BLUE}Pour rejoindre la session:${NC} tmux attach-session -t MCP"
    echo -e "${BLUE}Utilisation:${NC} Ctrl+b puis 0-3 pour naviguer entre les fenêtres"
    
    # Attacher la session
    tmux attach-session -t MCP
else
    echo -e "${YELLOW}⚠️ tmux n'est pas installé. Installation manuelle des composants...${NC}"
    
    # Test de connexion à LNBits
    echo -e "${BLUE}🔍 Test de la connexion LNBits...${NC}"
    python test_lnbits_connection.py || echo -e "${YELLOW}⚠️ Avertissement: La connexion LNBits a échoué${NC}"
    
    # Lancer les composants manuellement
    echo -e "${YELLOW}Pour lancer le serveur API:${NC} python server.py"
    echo -e "${YELLOW}Pour lancer la collecte de données:${NC} python run_test_system.py"
fi