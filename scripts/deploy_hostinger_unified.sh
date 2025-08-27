#!/bin/bash

# ============================================
# Script de déploiement unifié pour Hostinger
# MCP API + Token-for-Good
# ============================================

set -e

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
HOSTINGER_USER="feustey"
HOSTINGER_HOST="147.79.101.32"
HOSTINGER_PATH="/home/feustey/unified-production"

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   Déploiement Unifié Hostinger${NC}"
echo -e "${BLUE}   MCP API + Token-for-Good${NC}"
echo -e "${BLUE}==================================================${NC}"

# Fonction pour vérifier les prérequis
check_requirements() {
    echo -e "\n${YELLOW}📋 Vérification des prérequis...${NC}"
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker n'est pas installé${NC}"
        exit 1
    fi
    
    # Vérifier les fichiers nécessaires
    local required_files=(
        "docker-compose.hostinger-unified.yml"
        "config/nginx/hostinger-unified.conf"
        ".env.production"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}❌ Fichier manquant: $file${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}✅ Tous les prérequis sont satisfaits${NC}"
}

# Fonction pour préparer l'environnement
prepare_environment() {
    echo -e "\n${YELLOW}🔧 Préparation de l'environnement...${NC}"
    
    # Créer le fichier .env si nécessaire
    if [ ! -f ".env.production" ]; then
        cat > .env.production << 'EOF'
# Configuration MCP
JWT_SECRET_KEY=your-jwt-secret-key
SECRET_KEY=your-secret-key
LNBITS_ADMIN_KEY=your-lnbits-key
ANTHROPIC_API_KEY=your-anthropic-key

# Configuration T4G
T4G_JWT_SECRET=your-t4g-jwt-secret
T4G_API_KEY=your-t4g-api-key

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure-password-here
EOF
        echo -e "${YELLOW}⚠️  Fichier .env.production créé - Veuillez le configurer${NC}"
        exit 1
    fi
    
    # Créer les répertoires nécessaires
    mkdir -p mcp-data/{logs,data,rag,backups}
    mkdir -p t4g-data/{logs,uploads}
    mkdir -p logs/nginx
    mkdir -p backups/mongo
    mkdir -p config/prometheus
    
    # Créer le fichier .htpasswd pour le monitoring
    if [ ! -f "config/nginx/.htpasswd" ]; then
        echo -e "${YELLOW}Création du fichier .htpasswd pour le monitoring...${NC}"
        echo "admin:$(openssl passwd -apr1 admin123)" > config/nginx/.htpasswd
    fi
}

# Fonction pour construire les images
build_images() {
    echo -e "\n${YELLOW}🏗️  Construction des images Docker...${NC}"
    
    # Build MCP API
    if [ -d "../MCP" ]; then
        echo -e "${BLUE}Building MCP API...${NC}"
        docker build -t feustey/dazno:latest .
    fi
    
    # Build Token-for-Good (si présent)
    if [ -d "../token-for-good" ]; then
        echo -e "${BLUE}Building Token-for-Good API...${NC}"
        (cd ../token-for-good && docker build -t feustey/token-for-good:latest .)
    fi
}

# Fonction pour déployer sur Hostinger
deploy_to_hostinger() {
    echo -e "\n${YELLOW}🚀 Déploiement sur Hostinger...${NC}"
    
    # Créer le répertoire sur le serveur
    echo -e "${BLUE}Création du répertoire de production...${NC}"
    ssh ${HOSTINGER_USER}@${HOSTINGER_HOST} "mkdir -p ${HOSTINGER_PATH}"
    
    # Copier les fichiers
    echo -e "${BLUE}Copie des fichiers de configuration...${NC}"
    rsync -avz --exclude 'node_modules' --exclude '.git' \
        docker-compose.hostinger-unified.yml \
        .env.production \
        config/ \
        ${HOSTINGER_USER}@${HOSTINGER_HOST}:${HOSTINGER_PATH}/
    
    # Démarrer les services
    echo -e "${BLUE}Démarrage des services...${NC}"
    ssh ${HOSTINGER_USER}@${HOSTINGER_HOST} << 'ENDSSH'
cd /home/feustey/unified-production

# Arrêter les anciens conteneurs
docker-compose -f docker-compose.hostinger-unified.yml down || true

# Nettoyer les vieux conteneurs et images
docker system prune -f

# Charger les variables d'environnement
export $(cat .env.production | grep -v '^#' | xargs)

# Démarrer les nouveaux services
docker-compose -f docker-compose.hostinger-unified.yml up -d

# Vérifier le statut
sleep 10
docker-compose -f docker-compose.hostinger-unified.yml ps

# Afficher les logs des dernières 50 lignes
docker-compose -f docker-compose.hostinger-unified.yml logs --tail=50
ENDSSH
}

# Fonction pour vérifier le déploiement
verify_deployment() {
    echo -e "\n${YELLOW}🔍 Vérification du déploiement...${NC}"
    
    # Test MCP API
    echo -e "${BLUE}Test de l'API MCP...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" https://api.dazno.de/health | grep -q "200"; then
        echo -e "${GREEN}✅ MCP API est accessible${NC}"
    else
        echo -e "${RED}❌ MCP API n'est pas accessible${NC}"
    fi
    
    # Test Token-for-Good
    echo -e "${BLUE}Test de Token-for-Good...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" https://token-for-good.com/health | grep -q "200"; then
        echo -e "${GREEN}✅ Token-for-Good est accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Token-for-Good n'est pas encore accessible${NC}"
    fi
}

# Fonction pour configurer le firewall
configure_firewall() {
    echo -e "\n${YELLOW}🔒 Configuration du firewall...${NC}"
    
    ssh ${HOSTINGER_USER}@${HOSTINGER_HOST} << 'ENDSSH'
# Autoriser les ports nécessaires
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Bloquer l'accès direct aux ports des applications
sudo ufw deny 8000/tcp comment 'Block direct MCP access'
sudo ufw deny 8001/tcp comment 'Block direct T4G access'
sudo ufw deny 9090/tcp comment 'Block direct Prometheus access'
sudo ufw deny 3000/tcp comment 'Block direct Grafana access'
sudo ufw deny 6333/tcp comment 'Block direct Qdrant access'

# Recharger le firewall
sudo ufw reload

echo "Firewall configuré avec succès"
ENDSSH
}

# Fonction pour afficher le résumé
show_summary() {
    echo -e "\n${GREEN}==================================================${NC}"
    echo -e "${GREEN}   Déploiement Terminé !${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo -e "\n📊 ${BLUE}Résumé de la configuration:${NC}"
    echo -e "  • MCP API: https://api.dazno.de (port 8000 interne)"
    echo -e "  • Token-for-Good: https://token-for-good.com (port 8001 interne)"
    echo -e "  • MongoDB: Port 27017 (interne)"
    echo -e "  • Redis: Port 6379 (interne)"
    echo -e "  • Prometheus: http://localhost:8080/prometheus"
    echo -e "  • Grafana: http://localhost:8080/grafana"
    echo -e "\n${YELLOW}🔐 Sécurité:${NC}"
    echo -e "  • Tous les services backend sont accessibles uniquement via Nginx"
    echo -e "  • CORS configuré pour app.dazno.de"
    echo -e "  • SSL/TLS activé sur tous les domaines publics"
    echo -e "  • Monitoring protégé par authentification HTTP Basic"
}

# Fonction principale
main() {
    check_requirements
    prepare_environment
    
    # Demander confirmation
    echo -e "\n${YELLOW}⚠️  Prêt à déployer sur Hostinger${NC}"
    echo -e "Serveur: ${HOSTINGER_USER}@${HOSTINGER_HOST}"
    echo -e "Chemin: ${HOSTINGER_PATH}"
    read -p "Continuer ? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
        deploy_to_hostinger
        configure_firewall
        verify_deployment
        show_summary
    else
        echo -e "${RED}Déploiement annulé${NC}"
        exit 1
    fi
}

# Lancer le script
main "$@"