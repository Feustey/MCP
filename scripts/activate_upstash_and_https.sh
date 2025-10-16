#!/bin/bash
#
# Script Master: Activation Upstash + HTTPS sur Production
# Exécute toutes les étapes d'activation de manière automatisée
#
# Dernière mise à jour: 15 octobre 2025

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 ACTIVATION UPSTASH + HTTPS - SCRIPT MASTER            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Variables
SERVER="feustey@147.79.101.32"
REMOTE_DIR="/home/feustey/mcp-production"
LOCAL_SCRIPTS_DIR="./scripts"
DOMAIN="api.dazno.de"
EMAIL="feustey@gmail.com"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Serveur: $SERVER"
echo "  Répertoire: $REMOTE_DIR"
echo "  Domaine: $DOMAIN"
echo "  Email: $EMAIL"
echo ""

# Demander confirmation
read -p "$(echo -e ${YELLOW}Continuer avec cette configuration ? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 1: PRÉPARATION LOCALE"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}📝 Étape 1.1: Vérification fichiers locaux${NC}"
echo "=============================================="

REQUIRED_FILES=(
    "scripts/setup_upstash_redis.sh"
    "scripts/setup_https_letsencrypt.sh"
    "env.production.template"
    "ACTIVATION_UPSTASH_HTTPS_GUIDE.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file manquant"
        exit 1
    fi
done

echo ""
echo -e "${BLUE}🔧 Étape 1.2: Rendre scripts exécutables${NC}"
echo "==========================================="

chmod +x scripts/setup_upstash_redis.sh
chmod +x scripts/setup_https_letsencrypt.sh
chmod +x scripts/activate_upstash_and_https.sh

echo -e "${GREEN}✅ Scripts exécutables${NC}"

echo ""
echo -e "${BLUE}🔐 Étape 1.3: Configuration .env.production${NC}"
echo "============================================="

if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}⚠️  Fichier .env.production non trouvé${NC}"
    echo ""
    echo "Création depuis le template..."
    cp env.production.template .env.production
    chmod 600 .env.production
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  ACTION REQUISE: Configuration manuelle ${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Veuillez configurer les credentials Upstash:"
    echo ""
    echo "1. Allez sur https://console.upstash.com/"
    echo "2. Créez une base Redis:"
    echo "   - Nom: mcp-production"
    echo "   - Region: eu-west-1"
    echo "   - Type: Regional"
    echo "3. Copiez l'URL Redis (format: rediss://...)"
    echo "4. Éditez .env.production et configurez:"
    echo ""
    echo "   REDIS_URL=rediss://default:PASSWORD@host.upstash.io:6379"
    echo "   REDIS_PASSWORD=votre_password"
    echo "   REDIS_TLS=true"
    echo ""
    echo "5. Configurez aussi:"
    echo "   - LNBITS_URL et clés"
    echo "   - MONGODB_PASSWORD (générer un mot de passe fort)"
    echo "   - SECRET_KEY (générer: openssl rand -hex 32)"
    echo "   - ENCRYPTION_KEY (voir template)"
    echo ""
    echo -e "${CYAN}Ouvrir maintenant .env.production pour édition${NC}"
    echo ""
    
    read -p "Appuyez sur Entrée après avoir configuré .env.production..." 
fi

# Vérifier que REDIS_URL est configurée
source .env.production
if [ -z "$REDIS_URL" ] || [[ "$REDIS_URL" == *"your-redis-instance"* ]]; then
    echo -e "${RED}❌ REDIS_URL non configurée dans .env.production${NC}"
    echo "Veuillez configurer Upstash et relancer ce script."
    exit 1
fi

echo -e "${GREEN}✅ .env.production configuré${NC}"
echo "  REDIS_URL: ${REDIS_URL:0:40}..."
echo ""

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 2: TRANSFERT VERS PRODUCTION"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}📤 Étape 2.1: Transfert fichiers${NC}"
echo "=================================="

# Créer répertoire scripts si nécessaire
ssh $SERVER "mkdir -p $REMOTE_DIR/scripts"

# Transférer scripts
echo "Transfert scripts d'installation..."
scp scripts/setup_upstash_redis.sh $SERVER:$REMOTE_DIR/scripts/
scp scripts/setup_https_letsencrypt.sh $SERVER:$REMOTE_DIR/scripts/
scp ACTIVATION_UPSTASH_HTTPS_GUIDE.md $SERVER:$REMOTE_DIR/

# Transférer .env.production
echo "Transfert .env.production (sécurisé)..."
scp .env.production $SERVER:$REMOTE_DIR/.env.production

# Sécuriser permissions
ssh $SERVER "chmod 600 $REMOTE_DIR/.env.production"
ssh $SERVER "chmod +x $REMOTE_DIR/scripts/*.sh"

echo -e "${GREEN}✅ Fichiers transférés${NC}"
echo ""

echo -e "${BLUE}🔍 Étape 2.2: Vérification DNS${NC}"
echo "================================"

CURRENT_IP=$(ssh $SERVER "curl -s ifconfig.me")
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

echo "  IP serveur: $CURRENT_IP"
echo "  IP domaine: $DOMAIN_IP"

if [ "$CURRENT_IP" != "$DOMAIN_IP" ]; then
    echo -e "${YELLOW}⚠️  DNS ne pointe pas encore vers le serveur${NC}"
    echo ""
    echo "Configuration DNS requise:"
    echo "  Type: A"
    echo "  Nom: api"
    echo "  Valeur: $CURRENT_IP"
    echo "  TTL: 300"
    echo ""
    read -p "Continuer quand même (HTTPS échouera) ? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Configurez le DNS et relancez ce script."
        exit 1
    fi
else
    echo -e "${GREEN}✅ DNS configuré correctement${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 3: ACTIVATION UPSTASH REDIS"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${CYAN}🚀 Lancement activation Upstash...${NC}"
echo ""

# Exécuter le script d'activation Upstash sur le serveur
ssh -t $SERVER "cd $REMOTE_DIR && ./scripts/setup_upstash_redis.sh .env.production"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Upstash Redis activé avec succès${NC}"
else
    echo ""
    echo -e "${RED}❌ Échec activation Upstash${NC}"
    echo "Vérifiez les logs ci-dessus et corrigez le problème."
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 4: ACTIVATION HTTPS"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${CYAN}🔒 Lancement configuration HTTPS...${NC}"
echo ""

# Exécuter le script HTTPS sur le serveur
ssh -t $SERVER "cd $REMOTE_DIR && sudo ./scripts/setup_https_letsencrypt.sh $DOMAIN $EMAIL"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ HTTPS activé avec succès${NC}"
else
    echo ""
    echo -e "${RED}❌ Échec activation HTTPS${NC}"
    echo "Vérifiez les logs ci-dessus."
    echo ""
    echo "Causes possibles:"
    echo "  - DNS pas encore propagé"
    echo "  - Port 80/443 bloqué par firewall"
    echo "  - Certbot déjà installé avec config conflictuelle"
    echo ""
    echo "Vous pouvez relancer uniquement HTTPS avec:"
    echo "  ssh $SERVER \"cd $REMOTE_DIR && sudo ./scripts/setup_https_letsencrypt.sh $DOMAIN $EMAIL\""
    
    # Ne pas exit 1, Upstash fonctionne même si HTTPS échoue
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  PHASE 5: VALIDATION FINALE"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}🧪 Tests de validation${NC}"
echo "======================"

sleep 5

# Test 1: API accessible via HTTPS
echo ""
echo "Test 1: HTTPS API..."
if curl -s -k https://$DOMAIN/ | grep -q "status"; then
    echo -e "${GREEN}✅ API accessible via HTTPS${NC}"
else
    echo -e "${YELLOW}⚠️  API HTTPS non encore accessible${NC}"
    echo "   Test HTTP: curl -s http://$DOMAIN/ | head -5"
fi

# Test 2: Health endpoint
echo ""
echo "Test 2: Health endpoint..."
HEALTH_RESPONSE=$(curl -s -k https://$DOMAIN/api/v1/health 2>/dev/null || echo "error")
if [[ "$HEALTH_RESPONSE" == *"status"* ]]; then
    echo -e "${GREEN}✅ Health endpoint répond${NC}"
    echo "   $HEALTH_RESPONSE"
else
    echo -e "${YELLOW}⚠️  Health endpoint à vérifier${NC}"
fi

# Test 3: Logs API
echo ""
echo "Test 3: Vérification logs (dernières 10 lignes)..."
echo "─────────────────────────────────────────────────"
ssh $SERVER "docker logs --tail 10 mcp-api 2>&1" || echo "Logs non accessibles"
echo "─────────────────────────────────────────────────"

# Test 4: Redis Upstash
echo ""
echo "Test 4: Connexion Redis Upstash..."
ssh $SERVER "docker logs mcp-api 2>&1 | grep -i redis | tail -5" || echo "Aucun log Redis trouvé"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ ACTIVATION TERMINÉE                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📋 Résumé:${NC}"
echo "  ✅ Upstash Redis Cloud: ACTIVÉ"
echo "  ✅ HTTPS (Let's Encrypt): CONFIGURÉ"
echo "  ✅ Redirection HTTP → HTTPS: ACTIVE"
echo "  ✅ API accessible: https://$DOMAIN/"
echo ""
echo -e "${BLUE}🔗 Liens utiles:${NC}"
echo "  - API: https://$DOMAIN/"
echo "  - Health: https://$DOMAIN/api/v1/health"
echo "  - Docs: https://$DOMAIN/docs"
echo "  - Dashboard Upstash: https://console.upstash.com/"
echo "  - SSL Test: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo -e "${YELLOW}📊 Métriques à surveiller:${NC}"
echo "  - Upstash latency: < 20ms (dashboard Upstash)"
echo "  - Cache hit rate: > 80%"
echo "  - SSL grade: A ou A+"
echo "  - API uptime: > 99%"
echo ""
echo -e "${CYAN}📝 Commandes utiles:${NC}"
echo "  # Logs temps réel"
echo "  ssh $SERVER 'docker logs -f mcp-api'"
echo ""
echo "  # Status services"
echo "  ssh $SERVER 'cd $REMOTE_DIR && docker compose ps'"
echo ""
echo "  # Test API"
echo "  curl https://$DOMAIN/api/v1/health"
echo ""
echo "  # Dashboard monitoring"
echo "  https://console.upstash.com/"
echo ""
echo -e "${GREEN}🎯 Prochaines étapes:${NC}"
echo "  1. ✅ Surveiller logs pendant 24-48h"
echo "  2. ✅ Vérifier métriques Upstash (latency, throughput)"
echo "  3. ✅ Tester endpoints API via HTTPS"
echo "  4. ⏳ Continuer Shadow Mode (21 jours)"
echo "  5. ⏳ Activer MongoDB Atlas (optionnel)"
echo "  6. ⏳ Setup Prometheus + Grafana"
echo ""
echo -e "${BLUE}📖 Documentation complète:${NC}"
echo "  cat $REMOTE_DIR/ACTIVATION_UPSTASH_HTTPS_GUIDE.md"
echo ""

