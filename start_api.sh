#!/bin/bash
#
# Script de démarrage MCP API Production
# Utilisé par systemd et peut être exécuté manuellement
#
# Dernière mise à jour: 12 octobre 2025

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_DIR="${MCP_DIR:-$(dirname $(readlink -f $0))}"
VENV_DIR="$MCP_DIR/venv"
LOG_DIR="$MCP_DIR/logs"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"
HOST="${HOST:-0.0.0.0}"

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Changement de répertoire
cd "$MCP_DIR"
log_info "Working directory: $MCP_DIR"

# Vérifier que le virtualenv existe
if [ ! -d "$VENV_DIR" ]; then
    log_error "Virtual environment not found at $VENV_DIR"
    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    log_success "Virtual environment created"
fi

# Activer le virtualenv
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Vérifier les dépendances
if ! python -c "import fastapi" 2>/dev/null; then
    log_warning "Dependencies not installed, installing now..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    log_success "Dependencies installed"
fi

# Créer le répertoire logs si nécessaire
mkdir -p "$LOG_DIR"

# Charger les variables d'environnement
if [ -f "$MCP_DIR/.env" ]; then
    log_info "Loading environment variables from .env"
    set -a
    source "$MCP_DIR/.env"
    set +a
else
    log_warning ".env file not found, using defaults"
fi

# Définir PYTHONPATH
export PYTHONPATH="$MCP_DIR:$MCP_DIR/src:$PYTHONPATH"

# Vérifier que le port n'est pas déjà utilisé
if netstat -tuln 2>/dev/null | grep ":$PORT " > /dev/null; then
    log_error "Port $PORT is already in use!"
    log_info "Checking process..."
    lsof -i :$PORT || netstat -tulpn | grep ":$PORT"
    exit 1
fi

# Afficher la configuration
log_info "Configuration:"
log_info "  - Host: $HOST"
log_info "  - Port: $PORT"
log_info "  - Workers: $WORKERS"
log_info "  - Environment: ${ENVIRONMENT:-development}"
log_info "  - Log Level: ${LOG_LEVEL:-INFO}"

# Démarrer l'API
log_success "🚀 Starting MCP API..."
log_info "Logs: $LOG_DIR/api_direct.log"
log_info ""

exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "${LOG_LEVEL:-info}" \
    --access-log \
    --no-use-colors \
    --loop uvloop \
    --http httptools

