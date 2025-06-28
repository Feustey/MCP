#!/bin/bash
# Script complet de déploiement pour api.dazno.de
# Auteur: Stéphane Courant
# Date: Mai 2025

# Vérification des privilèges sudo
if ! sudo -n true 2>/dev/null; then
    echo "❌ Ce script nécessite des privilèges sudo"
    echo "Veuillez exécuter : sudo ./$(basename $0)"
    exit 1
fi

# Variables
DOMAIN="api.dazno.de"
APP_DIR="/var/www/mcp"
BACKUP_DIR="$APP_DIR/backups/deployment_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$APP_DIR/logs/deployment.log"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | sudo tee -a "$LOG_FILE"
}

# Création des répertoires nécessaires
sudo mkdir -p "$BACKUP_DIR/nginx" "$APP_DIR/logs"
sudo touch "$LOG_FILE"
sudo chown -R $(whoami):$(whoami) "$APP_DIR"

log "🚀 Début du déploiement pour $DOMAIN"

# 0. Nettoyage des conteneurs Docker existants
log "🧹 Nettoyage des conteneurs Docker..."
cd "$APP_DIR"
sudo docker-compose down || true
sudo docker ps -aq | xargs -r sudo docker rm -f || true

# 1. Sauvegarde de l'état actuel
log "📦 Sauvegarde de l'état actuel..."
sudo cp -r /etc/nginx/* "$BACKUP_DIR/nginx/"
if [ -f "$APP_DIR/docker-compose.yml" ]; then
    sudo docker-compose -f "$APP_DIR/docker-compose.yml" config > "$BACKUP_DIR/docker-compose.yml"
fi

# 2. Nettoyage initial
log "🧹 Nettoyage initial..."
sudo bash clean_nginx_config.sh || {
    log "❌ Erreur lors du nettoyage Nginx"
    exit 1
}

# 3. Déploiement SSL
log "🔒 Déploiement SSL..."
sudo bash deploy_ssl_complete.sh || {
    log "❌ Erreur lors du déploiement SSL"
    exit 1
}

# 4. Vérification du déploiement
log "🔍 Vérification du déploiement..."
sudo bash verify_ssl.sh || {
    log "❌ Erreur lors de la vérification SSL"
    exit 1
}

# 5. Construction et démarrage des conteneurs
log "🐳 Construction et démarrage des conteneurs..."
cd "$APP_DIR"
sudo docker-compose -f docker-compose.yml build --no-cache || {
    log "❌ Erreur lors de la construction des conteneurs"
    exit 1
}
sudo docker-compose -f docker-compose.yml up -d || {
    log "❌ Erreur lors du démarrage des conteneurs"
    exit 1
}

# 6. Test des endpoints critiques
log "🌐 Test des endpoints critiques..."
sleep 10  # Attente pour le démarrage des services
endpoints=("/health" "/docs" "/api/v1/status")
for endpoint in "${endpoints[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN$endpoint")
    if [ "$response" -eq 200 ]; then
        log "✅ Endpoint $endpoint : OK"
    else
        log "❌ Endpoint $endpoint : Erreur ($response)"
        exit 1
    fi
done

# 7. Configuration des sauvegardes automatiques
log "💾 Configuration des sauvegardes automatiques..."
(sudo crontab -l 2>/dev/null; echo "0 4 * * * /usr/bin/certbot renew --quiet") | sudo crontab -

# 8. Vérification finale
log "🔍 Vérification finale..."
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/health" | grep -q "200"; then
    log "✅ Déploiement terminé avec succès !"
    log "📊 Dashboard disponible sur https://$DOMAIN/docs"
else
    log "❌ Erreur lors de la vérification finale"
    exit 1
fi

# Résumé du déploiement
log "
📋 Résumé du déploiement :
- Domaine : $DOMAIN
- Backup : $BACKUP_DIR
- Logs : $LOG_FILE
- SSL : Actif et vérifié
- Nginx : Configuré et en cours d'exécution
- Services : Démarrés et vérifiés
" 