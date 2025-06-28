#!/bin/bash

# Script de configuration de l'environnement de production MCP
# Ce script génère le fichier .env.production avec les variables nécessaires

# Vérification que le script est exécuté depuis le bon répertoire
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "Erreur: Ce script doit être exécuté depuis le répertoire racine du projet"
    exit 1
fi

# Demande des valeurs nécessaires
read -p "Entrez votre clé API Sparkseer (sk_live_...) : " SPARKSEER_API_KEY
read -p "Entrez le mot de passe admin Grafana : " GRAFANA_ADMIN_PASSWORD
read -p "Entrez une clé secrète Grafana (32 caractères) : " GRAFANA_SECRET_KEY

# Validation des entrées
if [ -z "$SPARKSEER_API_KEY" ] || [ -z "$GRAFANA_ADMIN_PASSWORD" ] || [ -z "$GRAFANA_SECRET_KEY" ]; then
    echo "Erreur: Toutes les valeurs doivent être renseignées"
    exit 1
fi

if [ ${#GRAFANA_SECRET_KEY} -ne 32 ]; then
    echo "Erreur: La clé secrète Grafana doit faire exactement 32 caractères"
    exit 1
fi

# Création du fichier .env.production
cat > .env.production << EOL
# Configuration de l'environnement de production MCP

# API Sparkseer
SPARKSEER_API_KEY=${SPARKSEER_API_KEY}
SPARKSEER_BASE_URL=https://api.sparkseer.space

# Configuration Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
GRAFANA_SECRET_KEY=${GRAFANA_SECRET_KEY}

# Rate Limiting Sparkseer
RATE_LIMIT_SPARKSEER=200
DAILY_QUOTA_SPARKSEER=2000

# Origines autorisées
ALLOWED_ORIGINS=https://app.dazno.de

# Configuration des logs
LOG_LEVEL=INFO

# Configuration des workers
WORKERS=4
MAX_CONNECTIONS=100
EOL

# Sécurisation du fichier
chmod 600 .env.production

echo "Le fichier .env.production a été créé avec succès"
echo "Assurez-vous de sauvegarder ces informations de manière sécurisée"

# Couleurs pour la sortie
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔧 Configuration de l'environnement de production MCP..."

# Vérifier si le fichier .env.production existe déjà
if [ -f .env.production ]; then
    echo -e "${RED}⚠️  Le fichier .env.production existe déjà${NC}"
    read -p "Voulez-vous le remplacer ? (o/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        echo "❌ Opération annulée"
        exit 1
    fi
fi

# Copier le fichier de configuration sécurisé
echo "📝 Copie du fichier de configuration sécurisé..."
cp config/env.production.secure .env.production

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erreur lors de la copie du fichier${NC}"
    exit 1
fi

# Sécuriser les permissions
echo "🔒 Sécurisation des permissions..."
chmod 600 .env.production

# Configuration des variables manquantes
echo "⚙️ Configuration des variables d'environnement..."

# Construire l'URL MongoDB
MONGO_URL="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@mongodb:27017/${MONGO_INITDB_DATABASE}?authSource=admin"
echo "MONGO_URL=${MONGO_URL}" >> .env.production

# Générer une clé secrète pour la sécurité si elle n'existe pas
if ! grep -q "SECURITY_SECRET_KEY" .env.production; then
    SECURITY_KEY=$(openssl rand -base64 32)
    echo "SECURITY_SECRET_KEY=${SECURITY_KEY}" >> .env.production
fi

# Ajouter les variables LNBits
echo "LNBITS_ENDPOINT=https://legend.lnbits.com" >> .env.production
echo "LNBITS_INKEY=your_invoice_key" >> .env.production

# Ajouter la clé OpenAI
echo "AI_OPENAI_API_KEY=your_openai_key" >> .env.production

echo -e "${GREEN}✅ Configuration terminée${NC}"
echo "⚠️  N'oubliez pas de mettre à jour les clés API dans .env.production :"
echo "  - LNBITS_INKEY"
echo "  - AI_OPENAI_API_KEY"
echo "  - SPARKSEER_API_KEY (optionnel)"

# Redémarrer les services
echo "🔄 Redémarrage des services..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

echo -e "\n📋 Vérification des services :"
docker-compose -f docker-compose.prod.yml ps 