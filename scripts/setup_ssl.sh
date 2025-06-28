#!/bin/bash

# Script de configuration SSL pour MCP
# Dernière mise à jour: 7 mai 2025

# Vérification des privilèges root
if [ "$EUID" -ne 0 ]; then
    echo "Ce script doit être exécuté en tant que root"
    echo "Utilisez: sudo $0"
    exit 1
fi

set -e

# Configuration
DOMAIN="api.dazno.de"
EMAIL="admin@dazno.de"
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${WORKSPACE_DIR}/logs/ssl_setup_$(date +%Y%m%d_%H%M%S).log"

# Fonction de logging
log() {
    local message=$1
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
}

# Vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Vérification de certbot
    if ! command -v certbot >/dev/null 2>&1; then
        log "❌ Certbot n'est pas installé"
        log "📦 Installation de Certbot..."
        
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update
            apt-get install -y certbot python3-certbot-nginx
        elif command -v dnf >/dev/null 2>&1; then
            dnf install -y certbot python3-certbot-nginx
        elif command -v brew >/dev/null 2>&1; then
            brew install certbot
        else
            log "❌ Impossible d'installer Certbot automatiquement"
            log "📝 Veuillez installer Certbot manuellement : https://certbot.eff.org/instructions"
            exit 1
        fi
    fi
    
    # Création des répertoires nécessaires
    mkdir -p /etc/letsencrypt
    mkdir -p /var/log/letsencrypt
    mkdir -p /var/lib/letsencrypt
    
    # Configuration des permissions
    chown -R $(logname):$(id -gn $(logname)) /etc/letsencrypt
    chown -R $(logname):$(id -gn $(logname)) /var/log/letsencrypt
    chown -R $(logname):$(id -gn $(logname)) /var/lib/letsencrypt
    
    log "✅ Certbot est installé"
}

# Génération des certificats
generate_certificates() {
    log "🔒 Génération des certificats SSL pour ${DOMAIN}..."
    
    # Arrêt de Nginx s'il est en cours d'exécution
    if docker ps | grep -q mcp-nginx; then
        log "🛑 Arrêt de Nginx..."
        docker stop mcp-nginx || true
    fi
    
    # Génération des certificats
    log "🔑 Demande de certificats à Let's Encrypt..."
    certbot certonly \
        --standalone \
        --preferred-challenges http \
        --agree-tos \
        --email "$EMAIL" \
        --domain "$DOMAIN" \
        --non-interactive \
        --config-dir /etc/letsencrypt \
        --work-dir /var/lib/letsencrypt \
        --logs-dir /var/log/letsencrypt
    
    # Vérification des certificats
    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" ]; then
        log "✅ Certificats générés avec succès"
        
        # Configuration des permissions
        chmod 755 /etc/letsencrypt/live
        chmod 755 /etc/letsencrypt/archive
        chown -R $(logname):$(id -gn $(logname)) /etc/letsencrypt/live
        chown -R $(logname):$(id -gn $(logname)) /etc/letsencrypt/archive
        
        # Configuration du renouvellement automatique
        log "⚙️ Configuration du renouvellement automatique..."
        (crontab -l 2>/dev/null; echo "0 0 1 * * certbot renew --quiet --deploy-hook 'docker restart mcp-nginx'") | crontab -
        
        log "✅ Renouvellement automatique configuré"
    else
        log "❌ Erreur lors de la génération des certificats"
        exit 1
    fi
}

# Redémarrage des services
restart_services() {
    log "🔄 Redémarrage des services..."
    
    if [ -f "${WORKSPACE_DIR}/docker-compose.hostinger-local.yml" ]; then
        docker-compose -f "${WORKSPACE_DIR}/docker-compose.hostinger-local.yml" up -d nginx
        log "✅ Services redémarrés"
    else
        log "❌ Fichier docker-compose.hostinger-local.yml non trouvé"
        exit 1
    fi
}

# Vérification finale
verify_setup() {
    log "🔍 Vérification de la configuration SSL..."
    
    # Test de la connexion HTTPS
    if curl -s -I "https://${DOMAIN}/health" | grep -q "200 OK"; then
        log "✅ Configuration SSL validée"
    else
        log "⚠️ La connexion HTTPS ne répond pas comme prévu"
        log "📝 Vérifiez les logs Nginx pour plus de détails"
    fi
}

# Fonction principale
main() {
    # Création du répertoire de logs
    mkdir -p "$(dirname "$LOG_FILE")"
    chown -R $(logname):$(id -gn $(logname)) "$(dirname "$LOG_FILE")"
    
    log "🎬 Début de la configuration SSL pour MCP"
    
    # Exécution des étapes
    check_prerequisites
    generate_certificates
    restart_services
    verify_setup
    
    log "🎉 Configuration SSL terminée avec succès!"
    log "📝 Logs disponibles dans: $LOG_FILE"
    log "🌍 Site accessible sur: https://${DOMAIN}"
}

# Exécution du script
main "$@" 