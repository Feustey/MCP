#!/bin/bash
# Script de configuration de la nouvelle clé SSH pour Hostinger
# Dernière mise à jour: 7 janvier 2025

set -e

# Configuration
NEW_SSH_KEY="/Users/stephanecourant/.ssh/id_ed25519"
NEW_SSH_PUB_KEY="/Users/stephanecourant/.ssh/id_ed25519.pub"
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
REMOTE_HOST_ALT="srv782904.hostinger.com"
BACKUP_DIR="backups/ssh_config_$(date +%Y%m%d_%H%M%S)"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Vérification des prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérifier que la nouvelle clé SSH existe
    if [ ! -f "$NEW_SSH_KEY" ]; then
        error "Clé SSH privée non trouvée: $NEW_SSH_KEY"
    fi
    
    if [ ! -f "$NEW_SSH_PUB_KEY" ]; then
        error "Clé SSH publique non trouvée: $NEW_SSH_PUB_KEY"
    fi
    
    # Vérifier les permissions de la clé privée
    if [ "$(stat -f %Lp "$NEW_SSH_KEY")" != "600" ]; then
        log "Correction des permissions de la clé privée..."
        chmod 600 "$NEW_SSH_KEY"
    fi
    
    # Vérifier SSH
    if ! command -v ssh &> /dev/null; then
        error "SSH n'est pas installé"
    fi
    
    log "Prérequis vérifiés avec succès"
}

# Sauvegarde de l'ancienne configuration
backup_old_config() {
    log "Sauvegarde de l'ancienne configuration..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Sauvegarder l'ancien fichier id_ed25519.pub s'il existe
    if [ -f "id_ed25519.pub" ]; then
        cp "id_ed25519.pub" "$BACKUP_DIR/id_ed25519.pub.old"
        log "Ancien fichier id_ed25519.pub sauvegardé"
    fi
    
    # Sauvegarder les scripts modifiés
    for script in scripts/deploy_hostinger_secure.sh scripts/deploy-hostinger-rag.sh scripts/setup-hostinger-repo.sh scripts/update-hostinger.sh; do
        if [ -f "$script" ]; then
            cp "$script" "$BACKUP_DIR/$(basename "$script").old"
        fi
    done
    
    log "Sauvegarde terminée dans: $BACKUP_DIR"
}

# Test de connexion SSH avec la nouvelle clé
test_ssh_connection() {
    log "Test de connexion SSH avec la nouvelle clé..."
    
    # Tester avec l'IP
    if ssh -i "$NEW_SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "echo 'Connexion SSH OK'" &> /dev/null; then
        log "✓ Connexion SSH réussie avec $REMOTE_HOST"
        return 0
    fi
    
    # Tester avec le nom d'hôte alternatif
    if ssh -i "$NEW_SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST_ALT" "echo 'Connexion SSH OK'" &> /dev/null; then
        log "✓ Connexion SSH réussie avec $REMOTE_HOST_ALT"
        return 0
    fi
    
    warn "Connexion SSH échouée. La clé publique doit être ajoutée au serveur."
    return 1
}

# Ajout de la clé publique au serveur
add_public_key_to_server() {
    log "Ajout de la clé publique au serveur..."
    
    # Lire la clé publique
    PUBLIC_KEY_CONTENT=$(cat "$NEW_SSH_PUB_KEY")
    
    # Essayer d'ajouter la clé avec l'ancienne méthode (si disponible)
    if command -v sshpass &> /dev/null; then
        # Si sshpass est disponible, essayer avec mot de passe
        read -s -p "Mot de passe SSH pour $REMOTE_USER@$REMOTE_HOST: " SSH_PASS
        echo
        
        if sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/.ssh && echo '$PUBLIC_KEY_CONTENT' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" 2>/dev/null; then
            log "✓ Clé publique ajoutée avec succès"
            return 0
        fi
    fi
    
    # Méthode manuelle
    log "Méthode manuelle d'ajout de la clé publique:"
    echo "1. Connectez-vous au serveur: ssh $REMOTE_USER@$REMOTE_HOST"
    echo "2. Ajoutez cette clé publique à ~/.ssh/authorized_keys:"
    echo ""
    echo "$PUBLIC_KEY_CONTENT"
    echo ""
    echo "3. Ou utilisez cette commande:"
    echo "   echo '$PUBLIC_KEY_CONTENT' >> ~/.ssh/authorized_keys"
    echo "   chmod 600 ~/.ssh/authorized_keys"
    echo ""
    
    read -p "Appuyez sur Entrée une fois la clé ajoutée au serveur..."
    
    # Tester à nouveau la connexion
    if test_ssh_connection; then
        log "✓ Connexion SSH confirmée après ajout de la clé"
        return 0
    else
        error "Connexion SSH toujours échouée après ajout de la clé"
    fi
}

# Mise à jour des scripts de déploiement
update_deployment_scripts() {
    log "Mise à jour des scripts de déploiement..."
    
    # Mettre à jour deploy_hostinger_secure.sh
    if [ -f "scripts/deploy_hostinger_secure.sh" ]; then
        sed -i.bak "s|SSH_KEY=\"\$HOME/.ssh/mcp_deploy_key\"|SSH_KEY=\"$NEW_SSH_KEY\"|g" "scripts/deploy_hostinger_secure.sh"
        log "✓ scripts/deploy_hostinger_secure.sh mis à jour"
    fi
    
    # Mettre à jour deploy-hostinger-rag.sh
    if [ -f "scripts/deploy-hostinger-rag.sh" ]; then
        sed -i.bak "s|SSH_HOST=\"u123456789@your-hostinger-server.com\"|SSH_HOST=\"$REMOTE_USER@$REMOTE_HOST\"|g" "scripts/deploy-hostinger-rag.sh"
        log "✓ scripts/deploy-hostinger-rag.sh mis à jour"
    fi
    
    # Mettre à jour setup-hostinger-repo.sh
    if [ -f "scripts/setup-hostinger-repo.sh" ]; then
        sed -i.bak "s|SSH_HOST=\"feustey@srv782904.hostinger.com\"|SSH_HOST=\"$REMOTE_USER@$REMOTE_HOST\"|g" "scripts/setup-hostinger-repo.sh"
        log "✓ scripts/setup-hostinger-repo.sh mis à jour"
    fi
    
    # Mettre à jour update-hostinger.sh
    if [ -f "scripts/update-hostinger.sh" ]; then
        sed -i.bak "s|SSH_HOST=\"u123456789@your-hostinger-server.com\"|SSH_HOST=\"$REMOTE_USER@$REMOTE_HOST\"|g" "scripts/update-hostinger.sh"
        log "✓ scripts/update-hostinger.sh mis à jour"
    fi
    
    # Mettre à jour rebuild_and_deploy.sh
    if [ -f "scripts/rebuild_and_deploy.sh" ]; then
        sed -i.bak "s|~/.ssh/mcp_deploy_key|$NEW_SSH_KEY|g" "scripts/rebuild_and_deploy.sh"
        log "✓ scripts/rebuild_and_deploy.sh mis à jour"
    fi
}

# Création d'un fichier de configuration SSH local
create_ssh_config() {
    log "Création de la configuration SSH locale..."
    
    SSH_CONFIG="$HOME/.ssh/config"
    
    # Créer le fichier config s'il n'existe pas
    if [ ! -f "$SSH_CONFIG" ]; then
        touch "$SSH_CONFIG"
        chmod 600 "$SSH_CONFIG"
    fi
    
    # Ajouter la configuration pour Hostinger
    cat >> "$SSH_CONFIG" << EOF

# Configuration Hostinger MCP
Host hostinger-mcp
    HostName $REMOTE_HOST
    User $REMOTE_USER
    IdentityFile $NEW_SSH_KEY
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host hostinger-mcp-alt
    HostName $REMOTE_HOST_ALT
    User $REMOTE_USER
    IdentityFile $NEW_SSH_KEY
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF
    
    log "✓ Configuration SSH créée dans $SSH_CONFIG"
}

# Test final de la configuration
test_final_configuration() {
    log "Test final de la configuration..."
    
    # Tester avec la configuration SSH
    if ssh hostinger-mcp "echo 'Test de connexion avec alias SSH OK'" &> /dev/null; then
        log "✓ Connexion avec alias SSH réussie"
    else
        warn "Connexion avec alias SSH échouée, test avec IP directe..."
        if ssh -i "$NEW_SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "echo 'Test de connexion directe OK'" &> /dev/null; then
            log "✓ Connexion directe réussie"
        else
            error "Connexion SSH échouée"
        fi
    fi
}

# Affichage des informations de configuration
show_configuration_info() {
    log "Configuration terminée avec succès!"
    echo ""
    echo "🔑 Informations de configuration SSH:"
    echo "  • Clé privée: $NEW_SSH_KEY"
    echo "  • Clé publique: $NEW_SSH_PUB_KEY"
    echo "  • Serveur: $REMOTE_HOST ($REMOTE_HOST_ALT)"
    echo "  • Utilisateur: $REMOTE_USER"
    echo ""
    echo "📝 Commandes utiles:"
    echo "  • Connexion directe: ssh -i $NEW_SSH_KEY $REMOTE_USER@$REMOTE_HOST"
    echo "  • Connexion avec alias: ssh hostinger-mcp"
    echo "  • Déploiement sécurisé: ./scripts/deploy_hostinger_secure.sh"
    echo "  • Déploiement RAG: ./scripts/deploy-hostinger-rag.sh"
    echo ""
    echo "💾 Sauvegarde: $BACKUP_DIR"
    echo ""
    echo "🔧 Scripts mis à jour:"
    echo "  • deploy_hostinger_secure.sh"
    echo "  • deploy-hostinger-rag.sh"
    echo "  • setup-hostinger-repo.sh"
    echo "  • update-hostinger.sh"
    echo "  • rebuild_and_deploy.sh"
}

# Fonction principale
main() {
    log "🔧 Configuration de la nouvelle clé SSH pour Hostinger"
    log "Clé SSH: $NEW_SSH_KEY"
    log "Serveur: $REMOTE_HOST"
    echo ""
    
    check_prerequisites
    backup_old_config
    
    if ! test_ssh_connection; then
        add_public_key_to_server
    fi
    
    update_deployment_scripts
    create_ssh_config
    test_final_configuration
    show_configuration_info
    
    log "✅ Configuration SSH terminée avec succès!"
}

# Gestion des erreurs
trap 'error "Erreur lors de la configuration SSH"' ERR

# Exécution
main "$@" 