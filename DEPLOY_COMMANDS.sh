#!/bin/bash

################################################################################
# Commandes de Déploiement MCP sur Hostinger
# 
# À exécuter sur le serveur Hostinger après avoir uploadé les fichiers
#
# Usage: Copier-coller ces commandes une par une dans votre terminal SSH
################################################################################

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     🚀 DÉPLOIEMENT MCP SUR HOSTINGER                            ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# ÉTAPE 1: INSTALLATION DES PRÉREQUIS
# =============================================================================
echo "📦 Étape 1/5 : Installation des prérequis..."
echo ""

# Docker
if ! command -v docker &> /dev/null; then
    echo "Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installé"
else
    echo "✅ Docker déjà installé"
fi

# Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installation de Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installé"
else
    echo "✅ Docker Compose déjà installé"
fi

# Nginx + Certbot
if ! command -v nginx &> /dev/null; then
    echo "Installation de Nginx + Certbot..."
    sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
    echo "✅ Nginx + Certbot installés"
else
    echo "✅ Nginx déjà installé"
fi

echo ""
echo "⚠️  IMPORTANT: Si Docker vient d'être installé, déconnectez-vous et reconnectez-vous !"
echo "   Commande: exit puis ssh user@serveur"
echo ""
read -p "Appuyez sur Entrée pour continuer..."

# =============================================================================
# ÉTAPE 2: PRÉPARATION DU RÉPERTOIRE
# =============================================================================
echo ""
echo "📁 Étape 2/5 : Préparation du répertoire..."
echo ""

cd /opt
if [ ! -d "mcp" ]; then
    sudo mkdir -p mcp
    sudo chown $USER:$USER mcp
    echo "✅ Répertoire /opt/mcp créé"
else
    echo "✅ Répertoire /opt/mcp existe"
fi

cd mcp

# Extraction du package (si uploadé)
if [ -f "/tmp/mcp-deployment-package.tar.gz" ]; then
    echo "Extraction du package de déploiement..."
    tar -xzf /tmp/mcp-deployment-package.tar.gz
    echo "✅ Package extrait"
fi

# Vérifier les fichiers
echo ""
echo "Fichiers présents:"
ls -lh docker-compose.production.yml deploy_to_hostinger.sh config_production_hostinger.env 2>/dev/null || echo "⚠️  Fichiers manquants"
echo ""

# =============================================================================
# ÉTAPE 3: CONFIGURATION
# =============================================================================
echo ""
echo "⚙️  Étape 3/5 : Configuration..."
echo ""

# Copier le template
if [ ! -f ".env.production" ]; then
    cp config_production_hostinger.env .env.production
    echo "✅ Fichier .env.production créé"
else
    echo "⚠️  .env.production existe déjà"
    read -p "Voulez-vous le remplacer ? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp config_production_hostinger.env .env.production
        echo "✅ .env.production remplacé"
    fi
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  CONFIGURATION REQUISE                                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Éditez .env.production et remplissez:"
echo ""
echo "  OBLIGATOIRE:"
echo "    • ANTHROPIC_API_KEY=sk-ant-api03-xxxxx"
echo ""
echo "  OPTIONNEL:"
echo "    • LNBITS_URL=https://..."
echo "    • LNBITS_ADMIN_KEY=xxxxx"
echo "    • TELEGRAM_BOT_TOKEN=xxxxx"
echo "    • TELEGRAM_CHAT_ID=xxxxx"
echo ""
echo "  ✅ Déjà configuré (local Docker):"
echo "    • MongoDB (mongodb://mcp_admin:...@mongodb:27017/mcp_prod)"
echo "    • Redis (redis://:...@redis:6379/0)"
echo ""
echo "Commande: nano .env.production"
echo ""
read -p "Appuyez sur Entrée quand vous avez terminé l'édition..."

# =============================================================================
# ÉTAPE 4: DÉPLOIEMENT
# =============================================================================
echo ""
echo "🚀 Étape 4/5 : Déploiement..."
echo ""

# Rendre le script exécutable
chmod +x deploy_to_hostinger.sh
chmod +x scripts/*.sh

echo "Lancement du déploiement automatique..."
echo ""

./deploy_to_hostinger.sh

# =============================================================================
# ÉTAPE 5: VALIDATION
# =============================================================================
echo ""
echo "✅ Étape 5/5 : Validation..."
echo ""

sleep 5

# Validation automatique
if [ -f "scripts/validate_deployment.sh" ]; then
    ./scripts/validate_deployment.sh
else
    echo "⚠️  Script de validation non trouvé"
    
    # Validation manuelle
    echo "Validation manuelle..."
    
    # Vérifier les conteneurs
    echo ""
    echo "1. Conteneurs Docker:"
    docker-compose -f docker-compose.production.yml ps
    
    # Test API
    echo ""
    echo "2. Test API:"
    sleep 5
    curl -s http://localhost:8000/ | head -5 || echo "⚠️  API ne répond pas encore"
    
    # Test MongoDB
    echo ""
    echo "3. Test MongoDB:"
    docker exec mcp-mongodb-prod mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null && echo "✅ MongoDB OK" || echo "⚠️  MongoDB KO"
    
    # Test Redis
    echo ""
    echo "4. Test Redis:"
    docker exec mcp-redis-prod redis-cli -a mcp_redis_password_2025 ping 2>/dev/null && echo "✅ Redis OK" || echo "⚠️  Redis KO"
fi

# =============================================================================
# RÉSUMÉ
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     🎉 DÉPLOIEMENT TERMINÉ !                                    ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔗 URLs d'accès:"
echo "   • API locale:  http://localhost:8000/"
echo "   • Via Nginx:   http://localhost/"
echo "   • HTTPS:       https://api.dazno.de/ (si SSL configuré)"
echo "   • Docs:        https://api.dazno.de/docs"
echo ""
echo "📊 Commandes utiles:"
echo "   • Logs:        docker-compose -f docker-compose.production.yml logs -f"
echo "   • Status:      docker-compose -f docker-compose.production.yml ps"
echo "   • Restart:     docker-compose -f docker-compose.production.yml restart"
echo "   • Monitoring:  python3 monitor_production.py"
echo ""
echo "⚠️  MODE SHADOW ACTIVÉ (DRY_RUN=true)"
echo "   Le système observe sans appliquer de changements réels"
echo "   Observez pendant 7-14 jours avant de désactiver"
echo ""
echo "📚 Documentation:"
echo "   • START_HERE_DEPLOY.txt"
echo "   • MONGODB_REDIS_LOCAL_CHANGES.md"
echo ""
echo "✅ Déploiement réussi !"
echo ""

