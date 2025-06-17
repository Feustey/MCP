#!/bin/bash
# Script de build simplifié pour MCP avec Nixpacks
# Version corrective pour éviter les problèmes de syntaxe

set -euo pipefail

# Configuration
PROJECT_NAME="mcp-lightning-optimizer"

# Couleurs pour les logs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Vérification des prérequis
check_requirements() {
    log "🔍 Vérification des prérequis..."
    
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        error "Variable OPENAI_API_KEY manquante"
    fi
    
    if [[ ! -f "nixpacks.toml" ]]; then
        error "Fichier nixpacks.toml manquant"
    fi
    
    log "✅ Prérequis validés"
}

# Installation de Nixpacks si nécessaire
install_nixpacks() {
    if ! command -v nixpacks &> /dev/null; then
        log "📦 Installation de Nixpacks..."
        curl -sSL https://nixpacks.com/install.sh | bash
        export PATH="$HOME/.nixpacks/bin:$PATH"
        log "✅ Nixpacks installé"
    else
        log "✅ Nixpacks déjà installé"
    fi
}

# Build avec Nixpacks (syntaxe correcte)
build_app() {
    log "🔨 Build de l'application avec Nixpacks..."
    
    # Build avec la syntaxe correcte
    nixpacks build . \
        --name "$PROJECT_NAME" \
        --config nixpacks.toml \
        --env ENVIRONMENT=production \
        --env PORT=8000 \
        --verbose
    
    if [[ $? -eq 0 ]]; then
        log "✅ Build réussi"
    else
        error "❌ Échec du build"
    fi
}

# Test rapide de l'image
test_image() {
    log "🧪 Test rapide de l'image..."
    
    # Vérifier que l'image existe
    if docker images "$PROJECT_NAME" | grep -q "$PROJECT_NAME"; then
        log "✅ Image créée avec succès"
        
        # Afficher les détails de l'image
        docker images "$PROJECT_NAME"
    else
        error "❌ Image non trouvée"
    fi
}

# Fonction principale
main() {
    log "🚀 Build MCP Lightning Optimizer"
    
    check_requirements
    install_nixpacks
    build_app
    test_image
    
    log "🎉 Build terminé avec succès!"
    log "💡 Pour tester localement: docker run -p 8000:8000 -e OPENAI_API_KEY='$OPENAI_API_KEY' $PROJECT_NAME"
}

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 