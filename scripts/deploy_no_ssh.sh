#!/bin/sh

# Script de déploiement sans SSH pour api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🚀 Déploiement sans SSH pour api.dazno.de..."

echo "📋 Instructions de déploiement manuel:"
echo ""
echo "1. 🔑 Accès au serveur:"
echo "   - Connectez-vous à votre panneau de contrôle Hostinger"
echo "   - Ou utilisez le terminal SSH de Hostinger"
echo ""

echo "2. 📁 Préparation:"
echo "   mkdir -p /var/www/mcp"
echo "   cd /var/www/mcp"
echo ""

echo "3. 📦 Téléchargement:"
echo "   git clone https://github.com/Feustey/MCP.git ."
echo ""

echo "4. 🐍 Python:"
echo "   apt update && apt install -y python3 python3-pip python3-venv"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements-hostinger.txt"
echo ""

echo "5. 🔧 Service systemd:"
echo "   # Créer /etc/systemd/system/mcp-api.service"
echo "   # Voir le contenu dans le script deploy_api_dazno.sh"
echo ""

echo "6. 🌐 Caddy:"
echo "   # Configurer /etc/caddy/Caddyfile"
echo "   # Voir le contenu dans le script deploy_api_dazno.sh"
echo ""

echo "7. 🚀 Démarrage:"
echo "   systemctl daemon-reload"
echo "   systemctl enable mcp-api"
echo "   systemctl start mcp-api"
echo "   systemctl restart caddy"
echo ""

echo "✅ Instructions terminées" 