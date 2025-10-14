#!/bin/bash
#
# Configuration de logrotate pour MCP API
# Gère la rotation automatique des logs
#
# Dernière mise à jour: 12 octobre 2025
# Requiert: Accès sudo

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo "╔════════════════════════════════════════════════════════╗"
echo "║  📋 CONFIGURATION LOGROTATE POUR MCP                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Vérifier sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  Ce script requiert sudo"
    echo "Exécution: sudo $0"
    exit 1
fi

log_info "Installation de la configuration logrotate..."

# Copier la configuration
sudo cp config/logrotate.conf /etc/logrotate.d/mcp-api

# Permissions correctes
sudo chown root:root /etc/logrotate.d/mcp-api
sudo chmod 644 /etc/logrotate.d/mcp-api

log_success "Configuration installée"
echo ""

log_info "Test de la configuration..."

# Test de la configuration
if sudo logrotate -d /etc/logrotate.d/mcp-api 2>&1 | grep -q "error"; then
    echo "❌ Erreur dans la configuration"
    sudo logrotate -d /etc/logrotate.d/mcp-api
    exit 1
else
    log_success "✅ Configuration valide"
fi

echo ""
log_info "Force une rotation de test (dry-run)..."
sudo logrotate -f -v /etc/logrotate.d/mcp-api | head -20

echo ""
log_success "✅ Logrotate configuré avec succès"
echo ""
echo "📋 Configuration:"
echo "  - Rotation: Quotidienne"
echo "  - Rétention: 30 jours"
echo "  - Compression: Activée"
echo "  - Taille max par log: 100MB"
echo ""
echo "🔍 Commandes utiles:"
echo "  # Test de la config"
echo "  sudo logrotate -d /etc/logrotate.d/mcp-api"
echo ""
echo "  # Force une rotation"
echo "  sudo logrotate -f /etc/logrotate.d/mcp-api"
echo ""
echo "  # Voir les logs rotationnés"
echo "  ls -lh /home/feustey/mcp-production/logs/"

