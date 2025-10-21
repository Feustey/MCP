#!/bin/bash
# Script de déploiement des corrections MCP vers le serveur de production
# Date: 20 octobre 2025
#
# Usage: ./deploy_corrections.sh [SERVER_USER@SERVER_IP]

set -e

echo "🚀 Déploiement des Corrections MCP"
echo "==================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER=${1:-"feustey@147.79.101.32"}
REMOTE_PATH="/home/feustey/MCP"

echo "Configuration:"
echo "  Serveur: $SERVER"
echo "  Chemin distant: $REMOTE_PATH"
echo ""

# Vérifier que tous les fichiers existent
echo "📋 Vérification des fichiers..."
FILES_TO_DEPLOY=(
    "scripts/fix_mongodb_auth.sh"
    "scripts/check_ollama_models.sh"
    "scripts/test_deployment_complete.sh"
    "GUIDE_CORRECTION_RAPIDE_20OCT2025.md"
    "RAPPORT_CORRECTIONS_20OCT2025.md"
    "RESUME_SESSION_20OCT2025.md"
    "INDEX_CORRECTIONS_20OCT2025.md"
    "START_HERE_20OCT2025.md"
)

MISSING_FILES=0
for file in "${FILES_TO_DEPLOY[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Fichier manquant: $file${NC}"
        MISSING_FILES=$((MISSING_FILES + 1))
    else
        echo -e "${GREEN}✅ $file${NC}"
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ $MISSING_FILES fichier(s) manquant(s)${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Tous les fichiers sont présents${NC}"
echo ""

# Confirmer le déploiement
read -p "Voulez-vous déployer vers $SERVER? (o/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Oo]$ ]]; then
    echo "Déploiement annulé."
    exit 0
fi

echo ""
echo "📤 Déploiement en cours..."
echo ""

# Créer le répertoire distant si nécessaire
echo "1️⃣ Création des répertoires distants..."
ssh "$SERVER" "mkdir -p $REMOTE_PATH/scripts $REMOTE_PATH/docs/corrections_20oct2025"

# Copier les scripts
echo ""
echo "2️⃣ Copie des scripts..."
for script in scripts/fix_mongodb_auth.sh scripts/check_ollama_models.sh scripts/test_deployment_complete.sh; do
    echo "  Copie de $script..."
    scp "$script" "$SERVER:$REMOTE_PATH/$script"
done

# Rendre les scripts exécutables
echo ""
echo "3️⃣ Configuration des permissions..."
ssh "$SERVER" "chmod +x $REMOTE_PATH/scripts/*.sh"

# Copier la documentation
echo ""
echo "4️⃣ Copie de la documentation..."
for doc in GUIDE_CORRECTION_RAPIDE_20OCT2025.md RAPPORT_CORRECTIONS_20OCT2025.md RESUME_SESSION_20OCT2025.md INDEX_CORRECTIONS_20OCT2025.md START_HERE_20OCT2025.md; do
    echo "  Copie de $doc..."
    scp "$doc" "$SERVER:$REMOTE_PATH/docs/corrections_20oct2025/"
done

# Créer un lien symbolique vers START_HERE dans le répertoire principal
ssh "$SERVER" "cd $REMOTE_PATH && ln -sf docs/corrections_20oct2025/START_HERE_20OCT2025.md START_HERE.md"

echo ""
echo -e "${GREEN}✅ Déploiement terminé avec succès !${NC}"
echo ""

# Afficher les prochaines étapes
echo "═══════════════════════════════════════════════"
echo "📋 PROCHAINES ÉTAPES SUR LE SERVEUR"
echo "═══════════════════════════════════════════════"
echo ""
echo "1. Se connecter au serveur:"
echo "   ssh $SERVER"
echo ""
echo "2. Aller dans le répertoire MCP:"
echo "   cd $REMOTE_PATH"
echo ""
echo "3. Lire le guide de démarrage:"
echo "   cat START_HERE.md"
echo ""
echo "4. Suivre le guide de correction:"
echo "   cat docs/corrections_20oct2025/GUIDE_CORRECTION_RAPIDE_20OCT2025.md"
echo ""
echo "5. Exécuter les corrections (30-60 min):"
echo "   ./scripts/fix_mongodb_auth.sh"
echo "   ./scripts/check_ollama_models.sh"
echo "   ./scripts/test_deployment_complete.sh"
echo ""
echo "═══════════════════════════════════════════════"
echo ""

# Option pour se connecter directement
read -p "Voulez-vous vous connecter au serveur maintenant? (o/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo ""
    echo "🔌 Connexion au serveur..."
    ssh "$SERVER" "cd $REMOTE_PATH && bash"
else
    echo ""
    echo "✅ Déploiement terminé. Connectez-vous manuellement quand vous êtes prêt."
fi

