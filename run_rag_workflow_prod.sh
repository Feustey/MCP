#!/bin/bash
# run_rag_workflow_prod.sh

# Définir le répertoire de base
BASE_DIR=$(dirname $(realpath $0))
cd $BASE_DIR

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Créer le répertoire de logs s'il n'existe pas
mkdir -p logs

# Timestamp pour les logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/workflow_${TIMESTAMP}.log"

echo -e "${BLUE}=== Démarrage du workflow RAG assets (${TIMESTAMP}) - MODE PRODUCTION ===${NC}"
echo -e "${BLUE}Les logs seront enregistrés dans ${LOG_FILE}${NC}"

# Vérification de l'environnement Python
if [ -d "venv" ]; then
    echo -e "${GREEN}Activation de l'environnement virtuel...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Environnement virtuel non trouvé, utilisation de Python système...${NC}"
fi

# Vérifier MongoDB et afficher l'URL utilisée
echo -e "${YELLOW}Configuration de MongoDB pour la production...${NC}"
MONGO_URL=$(python3 -c "import config; print(config.MONGO_URL)")
echo -e "${GREEN}URL MongoDB: ${MONGO_URL}${NC}"

# Exporter l'URL MongoDB pour que les scripts l'utilisent
export MONGO_URL
export LNBITS_ADMIN_KEY="fddac5fb8bf64eec944c89255b98dac4"

# Vérifier la connexion à MongoDB
echo -e "${YELLOW}Vérification de la connexion à MongoDB...${NC}"
python3 -c "
import pymongo
import sys
try:
    client = pymongo.MongoClient('${MONGO_URL}', serverSelectionTimeoutMS=5000)
    client.server_info()
    print('Connexion à MongoDB établie avec succès.')
    sys.exit(0)
except Exception as e:
    print(f'Erreur de connexion à MongoDB: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}ERREUR: Impossible de se connecter à MongoDB. Vérifiez l'URL et que MongoDB est bien démarré.${NC}"
    echo -e "${YELLOW}Le workflow va continuer, mais certaines fonctionnalités pourraient ne pas fonctionner correctement.${NC}"
fi

# Vérifier Redis mais ne pas exiger son démarrage
echo -e "${YELLOW}Vérification de Redis...${NC}"
redis-cli ping >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Redis n'est pas en cours d'exécution. Certaines fonctionnalités pourraient être limitées.${NC}"
else
    echo -e "${GREEN}Redis est en cours d'exécution.${NC}"
fi

# Fonction pour exécuter une commande et vérifier son statut
run_command() {
    echo -e "${YELLOW}Exécution: $1${NC}"
    eval "$1" 2>&1 | tee -a "$LOG_FILE"
    return ${PIPESTATUS[0]}
}

# Créer le répertoire RAG_assets s'il n'existe pas
mkdir -p rag/RAG_assets/reports/feustey
mkdir -p rag/RAG_assets/reports/barcelona
mkdir -p rag/RAG_assets/market_data/network_snapshots
mkdir -p rag/RAG_assets/nodes
mkdir -p rag/RAG_assets/metrics
mkdir -p rag/RAG_assets/logs
mkdir -p collected_data

# Rendre les scripts exécutables
chmod +x rag_asset_generator.py
chmod +x rag_asset_generator_simple.py

echo -e "${BLUE}=== Mode PRODUCTION activé - Génération d'assets réels ===${NC}"

# Vérifier l'existence des répertoires et templates nécessaires
if [ ! -d "rag/RAG_assets/reports/feustey" ]; then
    echo -e "${YELLOW}Création du répertoire pour les rapports feustey${NC}"
    mkdir -p "rag/RAG_assets/reports/feustey"
fi

if [ ! -d "rag/RAG_assets/reports/barcelona" ]; then
    echo -e "${YELLOW}Création du répertoire pour les rapports barcelona${NC}"
    mkdir -p "rag/RAG_assets/reports/barcelona"
fi

if [ ! -f "rag/RAG_assets/reports/feustey/rapport_template.md" ]; then
    echo -e "${YELLOW}Le template de rapport pour feustey n'existe pas. Utilisez celui par défaut.${NC}"
fi

if [ ! -f "rag/RAG_assets/reports/barcelona/rapport_template.md" ]; then
    echo -e "${YELLOW}Le template de rapport pour barcelona n'existe pas. Utilisez celui par défaut.${NC}"
fi

echo -e "${BLUE}=== Lancement du workflow en mode PRODUCTION ===${NC}"

# Étape 1: Exécuter le script d'agrégation des données
echo -e "${BLUE}=== Étape 1: Agrégation des données ===${NC}"
run_command "python run_aggregation.py"
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Avertissement: L'agrégation des données a échoué. Tentative de continuer avec les données existantes.${NC}"
fi

# Étape 2: Optimisation feustey
echo -e "${BLUE}=== Étape 2: Optimisation des frais de feustey ===${NC}"
run_command "python feustey_fee_optimizer.py"
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Avertissement: L'optimisation des frais de feustey a échoué. Poursuite du workflow.${NC}"
fi

# Étape 3: Exécuter l'optimisation RAG pour feustey
echo -e "${BLUE}=== Étape 3: Optimisation RAG pour feustey ===${NC}"
run_command "python feustey_rag_optimization.py"
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Avertissement: L'optimisation RAG pour feustey a échoué. Poursuite du workflow.${NC}"
fi

# Étape 4: Générer les assets RAG complets (version simplifiée)
echo -e "${BLUE}=== Étape 4: Génération des assets RAG (version simplifiée) ===${NC}"
run_command "python rag_asset_generator_simple.py"
if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur: La génération des assets RAG a échoué.${NC}"
    exit 1
fi

# Vérification des résultats
FEUSTEY_REPORTS=$(ls -1 rag/RAG_assets/reports/feustey/ 2>/dev/null | wc -l)
BARCELONA_REPORTS=$(ls -1 rag/RAG_assets/reports/barcelona/ 2>/dev/null | wc -l)

echo -e "${BLUE}=== Rapport de génération des assets RAG ===${NC}"
echo -e "${GREEN}Rapports feustey: $FEUSTEY_REPORTS${NC}"
echo -e "${GREEN}Rapports barcelona: $BARCELONA_REPORTS${NC}"

# Créer un lien symbolique vers les derniers rapports
echo -e "${YELLOW}Création de liens vers les derniers rapports...${NC}"
LATEST_FEUSTEY=$(ls -t rag/RAG_assets/reports/feustey/*_feustey_analysis.md 2>/dev/null | head -n1)
LATEST_BARCELONA=$(ls -t rag/RAG_assets/reports/barcelona/*_barcelona_analysis.md 2>/dev/null | head -n1)

if [ -n "$LATEST_FEUSTEY" ]; then
    ln -sf "$LATEST_FEUSTEY" rag/RAG_assets/reports/feustey/latest_report.md
    echo -e "${GREEN}Lien vers le dernier rapport feustey créé.${NC}"
fi

if [ -n "$LATEST_BARCELONA" ]; then
    ln -sf "$LATEST_BARCELONA" rag/RAG_assets/reports/barcelona/latest_report.md
    echo -e "${GREEN}Lien vers le dernier rapport barcelona créé.${NC}"
fi

echo -e "${BLUE}=== Workflow RAG assets terminé avec succès (mode PRODUCTION) ===${NC}"
echo -e "${GREEN}Tous les assets ont été générés et sont disponibles dans le répertoire rag/RAG_assets/${NC}"
echo -e "${YELLOW}Pour consulter les logs complets: cat ${LOG_FILE}${NC}"

# Désactiver l'environnement virtuel si activé
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 