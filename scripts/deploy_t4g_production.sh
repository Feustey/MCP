#!/bin/bash

# ============================================
# Script de déploiement Token4Good (T4G) Production
# ============================================

set -e

echo "🚀 Déploiement Token4Good (T4G) en Production"
echo "============================================="

# Configuration
REMOTE_HOST="217.160.24.201"
REMOTE_USER="root"
REMOTE_DIR="/opt/daznode/token4good"
BACKUP_DIR="/opt/daznode/backups/t4g_$(date +%Y%m%d_%H%M%S)"

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Préparation du package de déploiement local
log_info "Préparation du package T4G..."

# Créer le dossier temporaire
TEMP_DIR=$(mktemp -d)
T4G_PACKAGE="$TEMP_DIR/token4good"
mkdir -p "$T4G_PACKAGE"

# Copier les fichiers T4G
cp -r src/token4good "$T4G_PACKAGE/"
cp src/api/token4good_endpoints.py "$T4G_PACKAGE/"
cp src/api/main.py "$T4G_PACKAGE/api_main.py"
cp requirements-t4g.txt "$T4G_PACKAGE/requirements.txt"
cp .env.t4g "$T4G_PACKAGE/.env"
cp -r docs/token4good "$T4G_PACKAGE/docs/"

# Créer le script de démarrage
cat > "$T4G_PACKAGE/start_t4g.sh" << 'EOF'
#!/bin/bash
source /opt/daznode/venv/bin/activate
cd /opt/daznode/token4good
export PYTHONPATH=/opt/daznode/token4good:$PYTHONPATH
python -m uvicorn api_main:app --host 0.0.0.0 --port 8001 --reload
EOF
chmod +x "$T4G_PACKAGE/start_t4g.sh"

# Créer le service systemd
cat > "$T4G_PACKAGE/token4good.service" << 'EOF'
[Unit]
Description=Token4Good (T4G) API Service
After=network.target mongodb.service redis.service
Requires=mongodb.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/daznode/token4good
Environment="PYTHONPATH=/opt/daznode/token4good"
ExecStart=/opt/daznode/venv/bin/python -m uvicorn api_main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Créer l'archive
cd "$TEMP_DIR"
tar -czf token4good.tar.gz token4good/

log_info "Package T4G créé: $TEMP_DIR/token4good.tar.gz"

# 2. Déploiement sur le serveur
log_info "Connexion au serveur de production..."

# Transférer le package
scp -o StrictHostKeyChecking=no "$TEMP_DIR/token4good.tar.gz" $REMOTE_USER@$REMOTE_HOST:/tmp/

# Exécuter les commandes de déploiement sur le serveur
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST << 'REMOTE_SCRIPT'
set -e

echo "📦 Installation de Token4Good sur le serveur..."

# Créer une sauvegarde si le dossier existe
if [ -d "/opt/daznode/token4good" ]; then
    echo "Sauvegarde de l'ancienne version..."
    mkdir -p /opt/daznode/backups
    mv /opt/daznode/token4good /opt/daznode/backups/t4g_backup_$(date +%Y%m%d_%H%M%S)
fi

# Créer le dossier d'installation
mkdir -p /opt/daznode

# Extraire le package
cd /opt/daznode
tar -xzf /tmp/token4good.tar.gz
rm /tmp/token4good.tar.gz

# Créer l'environnement virtuel si nécessaire
if [ ! -d "/opt/daznode/venv" ]; then
    echo "Création de l'environnement virtuel Python..."
    python3 -m venv /opt/daznode/venv
fi

# Activer et installer les dépendances
source /opt/daznode/venv/bin/activate
cd /opt/daznode/token4good
pip install --upgrade pip
pip install -r requirements.txt

# Créer les dossiers nécessaires
mkdir -p /var/log/token4good

# Installer le service systemd
cp token4good.service /etc/systemd/system/
systemctl daemon-reload

# Configurer MongoDB pour T4G
mongosh << EOF
use token4good;
db.createCollection("users");
db.createCollection("transactions");
db.createCollection("services");
db.createCollection("bookings");
db.createCollection("sessions");
print("✅ Collections MongoDB T4G créées");
EOF

# Configurer Nginx pour T4G
cat > /etc/nginx/sites-available/token4good << 'NGINX_CONFIG'
# Token4Good API Configuration
location /api/v1/token4good/ {
    proxy_pass http://127.0.0.1:8001/api/v1/token4good/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    
    # CORS Headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    
    if ($request_method = 'OPTIONS') {
        return 204;
    }
}

# Documentation T4G
location /docs/token4good/ {
    alias /opt/daznode/token4good/docs/;
    try_files $uri $uri/ /index.html;
}
NGINX_CONFIG

# Ajouter la configuration au site principal
if ! grep -q "token4good" /etc/nginx/sites-available/api.dazno.de; then
    sed -i '/location \/ {/i\    include /etc/nginx/sites-available/token4good;' /etc/nginx/sites-available/api.dazno.de
fi

# Tester et recharger Nginx
nginx -t && systemctl reload nginx

# Démarrer le service T4G
systemctl enable token4good
systemctl restart token4good

# Attendre que le service démarre
sleep 5

# Vérifier le statut
if systemctl is-active --quiet token4good; then
    echo "✅ Service Token4Good démarré avec succès"
else
    echo "❌ Erreur lors du démarrage du service"
    journalctl -u token4good -n 50
    exit 1
fi

# Test de santé
echo "Test de l'API T4G..."
if curl -f -s http://localhost:8001/api/v1/token4good/admin/system/status > /dev/null; then
    echo "✅ API T4G répond correctement"
else
    echo "❌ L'API T4G ne répond pas"
    exit 1
fi

echo "🎉 Token4Good déployé avec succès !"
REMOTE_SCRIPT

# 3. Tests de validation
log_info "Tests de validation du déploiement..."

# Test de l'API publique
log_info "Test de l'endpoint public..."
if curl -f -s "https://api.dazno.de/api/v1/token4good/admin/system/status" > /dev/null; then
    log_info "✅ API T4G accessible publiquement"
else
    log_error "❌ API T4G non accessible sur le domaine public"
fi

# Créer un utilisateur de test
log_info "Création d'un utilisateur de test..."
TEST_RESPONSE=$(curl -s -X POST "https://api.dazno.de/api/v1/token4good/users" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "prod_test_user",
        "username": "ProductionTestUser",
        "email": "test@dazno.de",
        "skills": ["lightning-network", "testing"]
    }')

if echo "$TEST_RESPONSE" | grep -q "prod_test_user"; then
    log_info "✅ Utilisateur de test créé avec succès"
else
    log_error "❌ Échec de création de l'utilisateur de test"
fi

# Nettoyer les fichiers temporaires
rm -rf "$TEMP_DIR"

# 4. Rapport final
echo ""
echo "======================================"
echo "🎉 DÉPLOIEMENT T4G TERMINÉ AVEC SUCCÈS"
echo "======================================"
echo ""
echo "📍 Endpoints disponibles:"
echo "  - API: https://api.dazno.de/api/v1/token4good/"
echo "  - Docs: https://api.dazno.de/docs/token4good/"
echo "  - Status: https://api.dazno.de/api/v1/token4good/admin/system/status"
echo ""
echo "📊 Services actifs:"
echo "  - Token4Good API (port 8001)"
echo "  - MongoDB (collections T4G)"
echo "  - Redis (cache T4G)"
echo "  - Nginx (reverse proxy)"
echo ""
echo "🔧 Commandes utiles:"
echo "  - Status: systemctl status token4good"
echo "  - Logs: journalctl -u token4good -f"
echo "  - Restart: systemctl restart token4good"
echo ""
echo "✅ Le système Token4Good est maintenant en production !"