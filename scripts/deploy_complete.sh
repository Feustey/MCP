#!/bin/sh

# Script de déploiement complet pour api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🚀 Déploiement complet pour api.dazno.de..."

echo "📋 Instructions de déploiement:"
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

echo "4. 🐍 Configuration Python:"
echo "   apt update && apt install -y python3 python3-pip python3-venv"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements-hostinger.txt"
echo ""

echo "5. 🔧 Configuration du service systemd:"
echo "   # Copier le fichier de service:"
echo "   cp config/systemd/mcp-api.service /etc/systemd/system/"
echo "   # Ou créer manuellement le fichier /etc/systemd/system/mcp-api.service"
echo ""

echo "6. 🌐 Configuration Caddy:"
echo "   # Copier le fichier de configuration:"
echo "   cp config/caddy/Caddyfile.api.dazno.de /etc/caddy/Caddyfile"
echo "   # Ou créer manuellement le fichier /etc/caddy/Caddyfile"
echo ""

echo "7. 🚀 Démarrage des services:"
echo "   systemctl daemon-reload"
echo "   systemctl enable mcp-api"
echo "   systemctl start mcp-api"
echo "   systemctl restart caddy"
echo ""

echo "8. ✅ Vérification:"
echo "   # Vérifier le statut:"
echo "   systemctl status mcp-api"
echo "   systemctl status caddy"
echo "   "
echo "   # Vérifier les logs:"
echo "   journalctl -u mcp-api -f"
echo "   tail -f /var/log/caddy/api.dazno.de.log"
echo "   "
echo "   # Test local:"
echo "   curl http://localhost:8000/health"
echo ""

echo "9. 🔍 Diagnostic:"
echo "   # Vérifier les ports:"
echo "   netstat -tlnp | grep -E ':(80|443|8000)'"
echo "   "
echo "   # Vérifier les processus:"
echo "   ps aux | grep -E '(python|uvicorn|fastapi)'"
echo ""

echo "📞 Support:"
echo "Si vous rencontrez des problèmes:"
echo "1. Vérifiez les logs: journalctl -u mcp-api -f"
echo "2. Testez localement: curl http://localhost:8000/health"
echo "3. Vérifiez la configuration: cat /etc/caddy/Caddyfile"
echo "4. Redémarrez: systemctl restart mcp-api caddy"

echo ""
echo "✅ Instructions terminées" 