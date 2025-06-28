#!/bin/sh

# Script de déploiement et démarrage pour api.dazno.de
# Dernière mise à jour: 9 mai 2025

echo "🚀 Déploiement et démarrage de l'API sur api.dazno.de..."

# Configuration
REMOTE_HOST="api.dazno.de"
REMOTE_USER="root"  # Ajuster selon votre configuration
APP_DIR="/var/www/mcp"
SERVICE_NAME="mcp-api"

echo "📋 Configuration:"
echo "  Host: $REMOTE_HOST"
echo "  User: $REMOTE_USER"
echo "  App Dir: $APP_DIR"
echo "  Service: $SERVICE_NAME"

# 1. Vérifier la connectivité SSH
echo ""
echo "🔌 Test de connectivité SSH..."
ssh -o ConnectTimeout=10 -o BatchMode=yes $REMOTE_USER@$REMOTE_HOST "echo 'SSH OK'" || {
    echo "❌ Impossible de se connecter en SSH"
    echo "Vérifiez:"
    echo "  - Les clés SSH sont configurées"
    echo "  - L'utilisateur $REMOTE_USER existe"
    echo "  - Le port SSH est ouvert (22)"
    exit 1
}

# 2. Vérifier l'état actuel du serveur
echo ""
echo "📊 État actuel du serveur..."
ssh $REMOTE_USER@$REMOTE_HOST "
echo '=== Services actifs ==='
systemctl list-units --type=service --state=active | grep -E '(caddy|nginx|apache|mcp|fastapi)' || echo 'Aucun service web/API trouvé'

echo '=== Ports en écoute ==='
netstat -tlnp | grep -E ':(80|443|8000|8080)' || echo 'Aucun port web en écoute'

echo '=== Processus Python ==='
ps aux | grep -E '(python|uvicorn|fastapi)' | grep -v grep || echo 'Aucun processus Python trouvé'

echo '=== Répertoire de l\'app ==='
ls -la $APP_DIR 2>/dev/null || echo 'Répertoire $APP_DIR non trouvé'
"

# 3. Créer le répertoire de l'application si nécessaire
echo ""
echo "📁 Création du répertoire de l'application..."
ssh $REMOTE_USER@$REMOTE_HOST "
mkdir -p $APP_DIR
cd $APP_DIR
pwd
"

# 4. Copier les fichiers nécessaires
echo ""
echo "📦 Copie des fichiers..."
# Copier les fichiers essentiels
scp -r src/ $REMOTE_USER@$REMOTE_HOST:$APP_DIR/
scp -r app/ $REMOTE_USER@$REMOTE_HOST:$APP_DIR/
scp -r config/ $REMOTE_USER@$REMOTE_HOST:$APP_DIR/
scp requirements-hostinger.txt $REMOTE_USER@$REMOTE_HOST:$APP_DIR/requirements.txt
scp scripts/start_direct.sh $REMOTE_USER@$REMOTE_HOST:$APP_DIR/
scp scripts/start_robust.sh $REMOTE_USER@$REMOTE_HOST:$APP_DIR/

# 5. Configuration de l'environnement
echo ""
echo "⚙️ Configuration de l'environnement..."
ssh $REMOTE_USER@$REMOTE_HOST "
cd $APP_DIR

echo '=== Installation Python ==='
which python3 || {
    echo 'Installation de Python3...'
    apt update && apt install -y python3 python3-pip python3-venv
}

echo '=== Création de l\'environnement virtuel ==='
python3 -m venv venv
source venv/bin/activate

echo '=== Installation des dépendances ==='
pip install --upgrade pip
pip install -r requirements.txt

echo '=== Permissions ==='
chmod +x start_direct.sh start_robust.sh
"

# 6. Création du service systemd
echo ""
echo "🔧 Création du service systemd..."
ssh $REMOTE_USER@$REMOTE_HOST "
cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=MCP API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
"

# 7. Configuration Caddy
echo ""
echo "🌐 Configuration Caddy..."
ssh $REMOTE_USER@$REMOTE_HOST "
# Vérifier si Caddy est installé
which caddy || {
    echo 'Installation de Caddy...'
    apt install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt update && apt install caddy
}

# Configuration Caddy
cat > /etc/caddy/Caddyfile << 'EOF'
api.dazno.de {
    reverse_proxy localhost:8000
    log {
        output file /var/log/caddy/api.dazno.de.log
    }
}
EOF

systemctl restart caddy
"

# 8. Démarrage du service
echo ""
echo "🚀 Démarrage du service..."
ssh $REMOTE_USER@$REMOTE_HOST "
systemctl start $SERVICE_NAME
systemctl status $SERVICE_NAME --no-pager
"

# 9. Vérification
echo ""
echo "✅ Vérification du déploiement..."
sleep 5

# Test local sur le serveur
ssh $REMOTE_USER@$REMOTE_HOST "
echo '=== Test local ==='
curl -s -o /dev/null -w 'Local test - Code: %{http_code}\n' http://localhost:8000/health || echo 'Local test failed'

echo '=== Logs du service ==='
journalctl -u $SERVICE_NAME --no-pager -n 20

echo '=== Logs Caddy ==='
tail -n 10 /var/log/caddy/api.dazno.de.log 2>/dev/null || echo 'Logs Caddy non trouvés'
"

# 10. Test final
echo ""
echo "🎯 Test final de l'API..."
sleep 3
curl -s -o /dev/null -w "Test final - Code: %{http_code}\n" https://api.dazno.de/health || {
    echo "❌ L'API n'est toujours pas accessible"
    echo "Vérifiez les logs:"
    echo "  ssh $REMOTE_USER@$REMOTE_HOST 'journalctl -u $SERVICE_NAME -f'"
}

echo ""
echo "✅ Déploiement terminé"
echo ""
echo "📋 Commandes utiles:"
echo "  Status: ssh $REMOTE_USER@$REMOTE_HOST 'systemctl status $SERVICE_NAME'"
echo "  Logs: ssh $REMOTE_USER@$REMOTE_HOST 'journalctl -u $SERVICE_NAME -f'"
echo "  Restart: ssh $REMOTE_USER@$REMOTE_HOST 'systemctl restart $SERVICE_NAME'"
echo "  Stop: ssh $REMOTE_USER@$REMOTE_HOST 'systemctl stop $SERVICE_NAME'" 