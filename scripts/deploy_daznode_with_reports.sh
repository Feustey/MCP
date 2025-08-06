#!/bin/bash
# Script de déploiement MCP avec rapports Daznode sur Hostinger
# Inclut la reconstruction et le déploiement des conteneurs avec les nouvelles fonctionnalités

set -e

# Configuration
PROJECT_NAME="mcp-daznode"
DOCKER_IMAGE="feustey/dazno"
DOMAIN="api.dazno.de"
SSH_HOST="feustey@147.79.101.32"
SSH_PORT="22"
BUILD_TAG=$(date +%Y%m%d-%H%M)

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

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log "🔍 Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé. Installation requise."
    fi
    
    # Vérifier SSH
    if ! command -v ssh &> /dev/null; then
        error "SSH n'est pas installé"
    fi
    
    # Vérifier les fichiers requis
    if [ ! -f "Dockerfile.production" ]; then
        error "Dockerfile.production non trouvé"
    fi
    
    if [ ! -f "scripts/daily_daznode_report.py" ]; then
        error "Script de rapport Daznode non trouvé. Exécutez d'abord la configuration des rapports."
    fi
    
    log "✅ Prérequis validés"
}

# Construction de l'image Docker
build_image() {
    log "🔨 Construction de l'image Docker..."
    
    # Nettoyer les anciennes images
    docker image prune -f || true
    
    # Construire la nouvelle image
    info "Construction de l'image $DOCKER_IMAGE:$BUILD_TAG"
    docker build -f Dockerfile.production -t $DOCKER_IMAGE:$BUILD_TAG -t $DOCKER_IMAGE:latest .
    
    if [ $? -eq 0 ]; then
        log "✅ Image construite avec succès"
    else
        error "❌ Échec de la construction de l'image"
    fi
}

# Push vers Docker Hub
push_to_dockerhub() {
    log "📤 Push vers Docker Hub..."
    
    # Vérifier la connexion Docker Hub
    if ! docker info | grep -q "Username"; then
        warn "Non connecté à Docker Hub. Tentez de vous connecter:"
        docker login
    fi
    
    # Push des images
    info "Push de $DOCKER_IMAGE:$BUILD_TAG"
    docker push $DOCKER_IMAGE:$BUILD_TAG
    
    info "Push de $DOCKER_IMAGE:latest"
    docker push $DOCKER_IMAGE:latest
    
    log "✅ Images poussées sur Docker Hub"
}

# Test de connexion SSH
test_ssh_connection() {
    log "🔐 Test de la connexion SSH..."
    
    if ssh -o ConnectTimeout=10 -o BatchMode=yes $SSH_HOST "echo 'Connexion SSH réussie'" &> /dev/null; then
        log "✅ Connexion SSH opérationnelle"
    else
        error "❌ Impossible de se connecter via SSH à $SSH_HOST"
    fi
}

# Déploiement sur le serveur
deploy_to_server() {
    log "🚀 Déploiement sur le serveur de production..."
    
    # Créer le script de déploiement distant
    cat << 'EOF' > /tmp/remote_deploy.sh
#!/bin/bash
set -e

log() {
    echo -e "\033[0;32m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m $1"
}

error() {
    echo -e "\033[0;31m[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:\033[0m $1"
    exit 1
}

PROJECT_NAME="mcp-daznode"
DOCKER_IMAGE="feustey/dazno"
BUILD_TAG="__BUILD_TAG__"

log "🔄 Arrêt des anciens conteneurs..."
docker-compose -f docker-compose.hostinger-production.yml down --remove-orphans || true

log "📥 Pull des nouvelles images..."
docker pull $DOCKER_IMAGE:$BUILD_TAG
docker pull $DOCKER_IMAGE:latest

# Mise à jour du tag dans docker-compose si nécessaire
if [ -f docker-compose.hostinger-production.yml ]; then
    # Sauvegarder l'ancien fichier
    cp docker-compose.hostinger-production.yml docker-compose.hostinger-production.yml.bak
    
    # Mettre à jour l'image dans le docker-compose
    sed -i "s|image: $DOCKER_IMAGE:.*|image: $DOCKER_IMAGE:$BUILD_TAG|g" docker-compose.hostinger-production.yml
fi

log "🚀 Démarrage des nouveaux conteneurs..."
docker-compose -f docker-compose.hostinger-production.yml up -d

log "🧹 Nettoyage des anciennes images..."
docker image prune -f

log "✅ Déploiement terminé"

# Vérifier que les services sont démarrés
sleep 10
if docker-compose -f docker-compose.hostinger-production.yml ps | grep -q "Up"; then
    log "✅ Services démarrés avec succès"
    docker-compose -f docker-compose.hostinger-production.yml ps
else
    error "❌ Problème de démarrage des services"
fi
EOF

    # Remplacer le tag dans le script
    sed -i.bak "s/__BUILD_TAG__/$BUILD_TAG/g" /tmp/remote_deploy.sh
    
    # Copier et exécuter le script sur le serveur
    info "📋 Copie du script de déploiement..."
    scp /tmp/remote_deploy.sh $SSH_HOST:~/remote_deploy.sh
    
    info "🎯 Exécution du déploiement distant..."
    ssh $SSH_HOST "chmod +x ~/remote_deploy.sh && ~/remote_deploy.sh"
    
    # Nettoyer
    rm -f /tmp/remote_deploy.sh /tmp/remote_deploy.sh.bak
    
    log "✅ Déploiement distant terminé"
}

# Installation du cron pour les rapports
install_cron_on_server() {
    log "⏰ Installation de la planification des rapports..."
    
    # Créer le script d'installation du cron distant
    cat << 'EOF' > /tmp/install_cron_remote.sh
#!/bin/bash
set -e

log() {
    echo -e "\033[0;32m[$(date '+%Y-%m-%d %H:%M:%S')]\033[0m $1"
}

# Créer le répertoire de logs
mkdir -p logs

# Configurer le cron pour les rapports quotidiens
log "📅 Configuration du cron pour les rapports quotidiens..."

# Vérifier si la tâche existe déjà
if crontab -l 2>/dev/null | grep -q "daily_daznode_report.py"; then
    log "⚠️  Tâche cron existante trouvée, mise à jour..."
    # Supprimer l'ancienne tâche
    crontab -l 2>/dev/null | grep -v "daily_daznode_report.py" | crontab -
fi

# Ajouter la nouvelle tâche
(crontab -l 2>/dev/null; echo "# Rapport quotidien Daznode - 7h00 tous les jours") | crontab -
(crontab -l 2>/dev/null; echo "0 7 * * * cd ~/mcp && docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py >> logs/daznode_report.log 2>&1") | crontab -

log "✅ Planification des rapports configurée"
log "📊 Le rapport quotidien sera envoyé tous les jours à 7h00"

# Afficher la configuration
log "📋 Configuration cron actuelle:"
crontab -l | grep -A1 -B1 daznode || echo "Aucune tâche daznode trouvée"
EOF

    # Copier et exécuter le script sur le serveur
    info "📋 Installation de la planification sur le serveur..."
    scp /tmp/install_cron_remote.sh $SSH_HOST:~/install_cron_remote.sh
    
    ssh $SSH_HOST "chmod +x ~/install_cron_remote.sh && ~/install_cron_remote.sh"
    
    # Nettoyer
    rm -f /tmp/install_cron_remote.sh
    
    log "✅ Planification installée sur le serveur"
}

# Test des services déployés
test_deployment() {
    log "🧪 Test du déploiement..."
    
    # Test de l'API
    info "Test de l'endpoint de santé..."
    if ssh $SSH_HOST "curl -f https://$DOMAIN/health" &> /dev/null; then
        log "✅ API accessible et fonctionnelle"
    else
        warn "⚠️  API non accessible - Vérifiez la configuration"
    fi
    
    # Test des logs
    info "Vérification des logs récents..."
    ssh $SSH_HOST "cd ~/mcp && docker-compose -f docker-compose.hostinger-production.yml logs --tail=20 mcp-api-prod"
}

# Test manuel du rapport
test_report_generation() {
    log "📊 Test de génération du rapport Daznode..."
    
    info "Exécution manuelle du script de rapport..."
    ssh $SSH_HOST "cd ~/mcp && docker-compose -f docker-compose.hostinger-production.yml exec -T mcp-api-prod python3 scripts/daily_daznode_report.py"
    
    if [ $? -eq 0 ]; then
        log "✅ Test de génération du rapport réussi"
    else
        warn "⚠️  Problème lors du test du rapport - Vérifiez les variables d'environnement"
    fi
}

# Fonction principale
main() {
    log "🚀 Démarrage du déploiement MCP avec rapports Daznode"
    log "=============================================================="
    
    # Étapes du déploiement
    check_prerequisites
    build_image
    push_to_dockerhub
    test_ssh_connection
    deploy_to_server
    install_cron_on_server
    test_deployment
    
    # Test optionnel du rapport
    read -p "Voulez-vous tester la génération du rapport maintenant ? (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[OoYy]$ ]]; then
        test_report_generation
    fi
    
    log "=============================================================="
    log "🎉 Déploiement terminé avec succès!"
    log ""
    log "📊 Rapport quotidien configuré pour 7h00 tous les jours"
    log "🌐 API disponible sur: https://$DOMAIN"
    log "📈 Dashboard Grafana: https://$DOMAIN/grafana"
    log "📝 Logs: ssh $SSH_HOST 'tail -f ~/mcp/logs/daznode_report.log'"
    log ""
    log "⚠️  Assurez-vous que les variables d'environnement Telegram sont configurées:"
    log "   - TELEGRAM_BOT_TOKEN"
    log "   - TELEGRAM_CHAT_ID"
}

# Gestion des signaux
cleanup() {
    log "🛑 Interruption détectée - Nettoyage..."
    rm -f /tmp/remote_deploy.sh* /tmp/install_cron_remote.sh
    exit 1
}

trap cleanup SIGINT SIGTERM

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi