#!/bin/bash
# Script de correction de l'authentification MongoDB
# Date: 20 octobre 2025
#
# Corrige le problème d'authentification MongoDB identifié dans STATUT_DEPLOIEMENT_20OCT2025.md

set -e

echo "🔧 Correction de l'authentification MongoDB pour MCP"
echo "=================================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Charge les variables d'environnement
if [ -f .env ]; then
    source .env
    echo "✅ Fichier .env chargé"
else
    echo "❌ Fichier .env non trouvé"
    exit 1
fi

# Valeurs par défaut si non définies
MONGODB_USER=${MONGODB_USER:-mcpuser}
MONGODB_PASSWORD=${MONGODB_PASSWORD:-CHANGEZ_CE_MOT_DE_PASSE_MONGODB_123!}
MONGODB_DATABASE=${MONGODB_DATABASE:-mcp_prod}
MONGODB_CONTAINER=${MONGODB_CONTAINER:-mcp-mongodb}

echo "Configuration:"
echo "  - Utilisateur: $MONGODB_USER"
echo "  - Base de données: $MONGODB_DATABASE"
echo "  - Container: $MONGODB_CONTAINER"
echo ""

# Étape 1: Vérifier que le container MongoDB est actif
echo "📋 Étape 1: Vérification du container MongoDB..."
if ! docker ps | grep -q "$MONGODB_CONTAINER"; then
    echo -e "${RED}❌ Container MongoDB non actif${NC}"
    echo "Démarrer avec: docker-compose up -d mongodb"
    exit 1
fi
echo -e "${GREEN}✅ Container MongoDB actif${NC}"
echo ""

# Étape 2: Vérifier la connexion MongoDB de base
echo "📋 Étape 2: Test de connexion MongoDB..."
if docker exec "$MONGODB_CONTAINER" mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MongoDB accessible${NC}"
else
    echo -e "${RED}❌ MongoDB non accessible${NC}"
    exit 1
fi
echo ""

# Étape 3: Vérifier si l'utilisateur existe déjà
echo "📋 Étape 3: Vérification de l'utilisateur existant..."
USER_EXISTS=$(docker exec "$MONGODB_CONTAINER" mongosh admin --eval "db.getUser('$MONGODB_USER')" 2>/dev/null | grep -c "user: '$MONGODB_USER'" || echo "0")

if [ "$USER_EXISTS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  L'utilisateur $MONGODB_USER existe déjà${NC}"
    read -p "Voulez-vous le recréer? (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        echo "Suppression de l'utilisateur existant..."
        docker exec "$MONGODB_CONTAINER" mongosh admin --eval "db.dropUser('$MONGODB_USER')"
        echo -e "${GREEN}✅ Utilisateur supprimé${NC}"
    else
        echo "Passage à l'étape suivante..."
    fi
fi
echo ""

# Étape 4: Créer l'utilisateur avec les bons droits
echo "📋 Étape 4: Création/Mise à jour de l'utilisateur..."
docker exec "$MONGODB_CONTAINER" mongosh admin --eval "
db.createUser({
  user: '$MONGODB_USER',
  pwd: '$MONGODB_PASSWORD',
  roles: [
    { role: 'readWrite', db: '$MONGODB_DATABASE' },
    { role: 'dbAdmin', db: '$MONGODB_DATABASE' },
    { role: 'readWrite', db: 'admin' }
  ]
})
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Utilisateur créé/mis à jour avec succès${NC}"
else
    echo -e "${RED}❌ Échec de la création de l'utilisateur${NC}"
    exit 1
fi
echo ""

# Étape 5: Test d'authentification
echo "📋 Étape 5: Test d'authentification..."
AUTH_TEST=$(docker exec "$MONGODB_CONTAINER" mongosh \
    -u "$MONGODB_USER" \
    -p "$MONGODB_PASSWORD" \
    --authenticationDatabase admin \
    --eval "db.runCommand('ping')" 2>&1)

if echo "$AUTH_TEST" | grep -q '"ok" *: *1'; then
    echo -e "${GREEN}✅ Authentification réussie${NC}"
else
    echo -e "${RED}❌ Échec de l'authentification${NC}"
    echo "Détails: $AUTH_TEST"
    exit 1
fi
echo ""

# Étape 6: Créer la base de données et une collection de test
echo "📋 Étape 6: Initialisation de la base de données..."
docker exec "$MONGODB_CONTAINER" mongosh \
    -u "$MONGODB_USER" \
    -p "$MONGODB_PASSWORD" \
    --authenticationDatabase admin \
    "$MONGODB_DATABASE" \
    --eval "
    db.createCollection('_system_info');
    db._system_info.insertOne({
        created_at: new Date(),
        version: '1.0.0',
        purpose: 'MCP Production Database',
        corrected_by: 'fix_mongodb_auth.sh'
    });
    print('Base de données initialisée');
    "

echo -e "${GREEN}✅ Base de données initialisée${NC}"
echo ""

# Étape 7: Créer les indexes nécessaires pour le RAG
echo "📋 Étape 7: Création des indexes pour le RAG..."
docker exec "$MONGODB_CONTAINER" mongosh \
    -u "$MONGODB_USER" \
    -p "$MONGODB_PASSWORD" \
    --authenticationDatabase admin \
    "$MONGODB_DATABASE" \
    --eval "
    // Collection pour les documents RAG
    db.createCollection('rag_documents');
    db.rag_documents.createIndex({ 'document_id': 1 }, { unique: true });
    db.rag_documents.createIndex({ 'created_at': -1 });
    db.rag_documents.createIndex({ 'metadata.node_pubkey': 1 });
    
    // Collection pour les embeddings
    db.createCollection('rag_embeddings');
    db.rag_embeddings.createIndex({ 'document_id': 1 });
    db.rag_embeddings.createIndex({ 'chunk_id': 1 }, { unique: true });
    
    // Collection pour les queries
    db.createCollection('rag_queries');
    db.rag_queries.createIndex({ 'timestamp': -1 });
    db.rag_queries.createIndex({ 'query_hash': 1 });
    
    print('Indexes créés pour le RAG');
    "

echo -e "${GREEN}✅ Indexes RAG créés${NC}"
echo ""

# Étape 8: Vérification finale
echo "📋 Étape 8: Vérification finale..."
docker exec "$MONGODB_CONTAINER" mongosh \
    -u "$MONGODB_USER" \
    -p "$MONGODB_PASSWORD" \
    --authenticationDatabase admin \
    "$MONGODB_DATABASE" \
    --eval "
    print('Collections disponibles:');
    db.getCollectionNames().forEach(function(col) {
        print('  - ' + col);
    });
    print('');
    print('Statistiques:');
    print('  - Base: ' + db.getName());
    print('  - Collections: ' + db.getCollectionNames().length);
    "

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Configuration MongoDB terminée avec succès !${NC}"
echo "=================================================="
echo ""
echo "📝 Prochaines étapes:"
echo "  1. Redémarrer l'API MCP: docker-compose restart mcp-api"
echo "  2. Tester l'endpoint RAG: curl http://localhost:8000/api/v1/rag/health"
echo "  3. Vérifier les logs: docker-compose logs -f mcp-api"
echo ""
echo "🔗 Connection string MongoDB:"
echo "   mongodb://$MONGODB_USER:$MONGODB_PASSWORD@mongodb:27017/$MONGODB_DATABASE?authSource=admin"
echo ""

