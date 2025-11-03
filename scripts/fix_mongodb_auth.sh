#!/bin/bash
# scripts/fix_mongodb_auth.sh
# Correction de l'authentification MongoDB

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Correction de l'authentification MongoDB...${NC}"

# Attendre que MongoDB soit prêt
echo -e "${YELLOW}⏳ Attente de MongoDB...${NC}"
sleep 10

# Vérifier que le conteneur MongoDB est en cours d'exécution
if ! docker ps | grep -q "mcp-mongodb"; then
    echo -e "${RED}❌ Conteneur MongoDB non trouvé${NC}"
    exit 1
fi

# Vérifier si MongoDB est en mode auth
echo -e "${YELLOW}🔍 Vérification du mode d'authentification...${NC}"
AUTH_MODE=$(docker exec mcp-mongodb mongosh --eval "db.runCommand('getCmdLineOpts').parsed.security.authorization" --quiet 2>/dev/null || echo "disabled")

if [ "$AUTH_MODE" = "enabled" ]; then
    echo -e "${YELLOW}🔐 MongoDB est en mode authentification${NC}"
    
    # Essayer de se connecter sans authentification (si possible)
    echo -e "${YELLOW}🔓 Tentative de connexion sans auth...${NC}"
    if docker exec mcp-mongodb mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Connexion sans auth réussie${NC}"
        AUTH_DISABLED=true
    else
        echo -e "${RED}❌ Connexion sans auth échouée${NC}"
        AUTH_DISABLED=false
    fi
else
    echo -e "${GREEN}🔓 MongoDB n'est pas en mode authentification${NC}"
    AUTH_DISABLED=true
fi

# Si l'auth est désactivée, créer l'utilisateur
if [ "$AUTH_DISABLED" = "true" ]; then
    echo -e "${YELLOW}👤 Création de l'utilisateur mcpuser...${NC}"
    
    # Supprimer l'ancien utilisateur s'il existe
    docker exec mcp-mongodb mongosh --eval "
use admin;
try {
    db.dropUser('mcpuser');
    print('✅ Ancien utilisateur supprimé');
} catch (e) {
    print('ℹ️ Utilisateur n\'existait pas');
}
" > /dev/null 2>&1

    # Créer le nouvel utilisateur
    docker exec mcp-mongodb mongosh --eval "
use admin;
db.createUser({
    user: 'mcpuser',
    pwd: 'MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY',
    roles: [
        {role: 'readWrite', db: 'mcp_prod'},
        {role: 'dbAdmin', db: 'mcp_prod'},
        {role: 'readWrite', db: 'admin'}
    ]
});
print('✅ Utilisateur mcpuser créé');
" > /dev/null 2>&1

    # Tester l'authentification
    echo -e "${YELLOW}🧪 Test de l'authentification...${NC}"
    if docker exec mcp-mongodb mongosh -u mcpuser -p MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY --authenticationDatabase admin --eval "db.runCommand('ping')" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Authentification MongoDB réussie${NC}"
        exit 0
    else
        echo -e "${RED}❌ Échec de l'authentification MongoDB${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ MongoDB est en mode auth mais nous ne pouvons pas nous connecter${NC}"
    echo -e "${YELLOW}💡 Solution: Redémarrer MongoDB sans auth temporairement${NC}"
    
    # Arrêter MongoDB
    echo -e "${YELLOW}🛑 Arrêt de MongoDB...${NC}"
    docker-compose -f docker-compose.hostinger.yml stop mongodb
    
    # Démarrer MongoDB sans auth temporairement
    echo -e "${YELLOW}🚀 Démarrage de MongoDB sans auth...${NC}"
    docker run -d --name mcp-mongodb-temp --network mcp_mcp-network -v mongodb_data:/data/db mongo:7.0 mongod --noauth
    
    # Attendre que MongoDB soit prêt
    sleep 15
    
    # Créer l'utilisateur
    echo -e "${YELLOW}👤 Création de l'utilisateur...${NC}"
    docker exec mcp-mongodb-temp mongosh --eval "
use admin;
db.createUser({
    user: 'mcpuser',
    pwd: 'MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY',
    roles: [
        {role: 'readWrite', db: 'mcp_prod'},
        {role: 'dbAdmin', db: 'mcp_prod'},
        {role: 'readWrite', db: 'admin'}
    ]
});
print('✅ Utilisateur créé');
" > /dev/null 2>&1
    
    # Arrêter le conteneur temporaire
    docker stop mcp-mongodb-temp
    docker rm mcp-mongodb-temp
    
    # Redémarrer MongoDB avec auth
    echo -e "${YELLOW}🔄 Redémarrage de MongoDB avec auth...${NC}"
    docker-compose -f docker-compose.hostinger.yml up -d mongodb
    sleep 15
    
    # Tester l'authentification
    echo -e "${YELLOW}🧪 Test de l'authentification...${NC}"
    if docker exec mcp-mongodb mongosh -u mcpuser -p MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY --authenticationDatabase admin --eval "db.runCommand('ping')" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Authentification MongoDB réussie${NC}"
        exit 0
    else
        echo -e "${RED}❌ Échec de l'authentification MongoDB${NC}"
        exit 1
    fi
fi