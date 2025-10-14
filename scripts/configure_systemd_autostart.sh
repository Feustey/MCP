#!/bin/bash
#
# Configuration Systemd pour auto-restart MCP API
# Garantit que l'API démarre automatiquement au boot et se relance en cas de crash
#
# Dernière mise à jour: 10 octobre 2025
# Requiert: Accès sudo

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  ⚙️  CONFIGURATION SYSTEMD AUTO-RESTART MCP           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Vérifier si on a sudo
if ! sudo -n true 2>/dev/null; then
    echo "⚠️  Ce script requiert les privilèges sudo"
    echo "Exécution: sudo $0"
    exit 1
fi

# Variables
MCP_USER="${MCP_USER:-feustey}"
MCP_DIR="${MCP_DIR:-/home/feustey/mcp-production}"

echo "✍️  Étape 1/5: Création du service systemd"
echo "==========================================="
echo ""
echo "Configuration:"
echo "  - User: $MCP_USER"
echo "  - Directory: $MCP_DIR"
echo ""

# Créer le fichier service
sudo tee /etc/systemd/system/mcp-api.service > /dev/null << SYSTEMDCONF
[Unit]
Description=MCP Lightning Network Optimizer API
Documentation=https://docs.dazno.de/mcp
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$MCP_USER
Group=$MCP_USER
WorkingDirectory=$MCP_DIR

# Variables d'environnement
Environment="PYTHONPATH=$MCP_DIR:$MCP_DIR/src"
Environment="ENVIRONMENT=production"
Environment="LOG_LEVEL=INFO"
Environment="PORT=8000"

# Charger les variables du .env
EnvironmentFile=$MCP_DIR/.env

# Commande de démarrage
ExecStart=$MCP_DIR/start_api.sh

# Restart automatique
Restart=always
RestartSec=10
StartLimitInterval=200
StartLimitBurst=5

# Sécurité
NoNewPrivileges=true
PrivateTmp=true

# Limites ressources
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

# Logs
StandardOutput=append:$MCP_DIR/logs/api_systemd.log
StandardError=append:$MCP_DIR/logs/api_systemd_error.log
SyslogIdentifier=mcp-api

# Timeout
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
SYSTEMDCONF

echo "✅ Service systemd créé: /etc/systemd/system/mcp-api.service"
echo ""

echo "🔄 Étape 2/5: Reload systemd"
echo "============================"

sudo systemctl daemon-reload
echo "✅ Systemd rechargé"
echo ""

echo "🛑 Étape 3/5: Arrêt du processus manuel"
echo "========================================"

# Arrêter le processus uvicorn manuel
if pgrep -f "uvicorn.*app.main" > /dev/null; then
    echo "Arrêt du processus uvicorn manuel..."
    pkill -f "uvicorn.*app.main" || true
    sleep 3
    echo "✅ Processus manuel arrêté"
else
    echo "✅ Aucun processus manuel à arrêter"
fi

echo ""
echo "🚀 Étape 4/5: Activation et démarrage du service"
echo "================================================="

# Activer le service au boot
sudo systemctl enable mcp-api
echo "✅ Service activé au démarrage"

# Démarrer le service
sudo systemctl start mcp-api
echo "✅ Service démarré"

echo ""
echo "⏳ Attente 10 secondes pour le démarrage..."
sleep 10

echo ""
echo "📊 Étape 5/5: Vérification"
echo "=========================="

# Statut du service
echo "État du service:"
sudo systemctl status mcp-api --no-pager | head -15

echo ""
echo "🔍 Port 8000:"
if netstat -tuln | grep ":8000 " > /dev/null; then
    echo "✅ Port 8000 ouvert"
    netstat -tuln | grep ":8000"
else
    echo "❌ Port 8000 non ouvert"
fi

echo ""
echo "🏥 Test healthcheck:"
if curl -sf http://localhost:8000/; then
    echo ""
    echo "✅ API répond correctement !"
else
    echo "❌ API ne répond pas"
    echo ""
    echo "📄 Logs du service:"
    sudo journalctl -u mcp-api --no-pager -n 30
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✅ SYSTEMD CONFIGURÉ AVEC SUCCÈS                     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Commandes utiles:"
echo ""
echo "  # Voir le status"
echo "  sudo systemctl status mcp-api"
echo ""
echo "  # Voir les logs"
echo "  sudo journalctl -u mcp-api -f"
echo ""
echo "  # Redémarrer"
echo "  sudo systemctl restart mcp-api"
echo ""
echo "  # Arrêter"
echo "  sudo systemctl stop mcp-api"
echo ""
echo "  # Désactiver auto-start"
echo "  sudo systemctl disable mcp-api"
echo ""
echo "✅ L'API redémarrera automatiquement:"
echo "  - Au boot du serveur"
echo "  - En cas de crash"
echo "  - Après 10 secondes d'attente"
echo "  - Maximum 5 tentatives en 200 secondes"

