#!/bin/bash

# Script de déploiement LNBits simplifié sur Hostinger
# Dernière mise à jour: 7 janvier 2025

set -euo pipefail

# Configuration
REMOTE_USER="feustey"
REMOTE_HOST="147.79.101.32"
REMOTE_DIR="/home/$REMOTE_USER/feustey"
SSH_KEY="/Users/stephanecourant/.ssh/id_ed25519"
SSH_OPTIONS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=30"
SUDO_PWD="Feustey@AI!"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions utilitaires
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
    exit 1
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Vérification de la connectivité
check_connectivity() {
    info " Vérification de la connectivité SSH vers Hostinger..."
    
    if ! ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" "echo 'Connexion SSH OK'" &> /dev/null; then
        error "❌ Échec de la connexion SSH vers $REMOTE_USER@$REMOTE_HOST"
    fi
    
    success "✅ Connectivité SSH OK"
}

# Création du docker-compose LNBits
creer_compose_lnbits() {
    info " Création du docker-compose LNBits..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Création du docker-compose LNBits ==="
        cat > docker-compose.lnbits.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # LNBits - Service Lightning
  lnbits:
    image: lnbits/lnbits:latest
    container_name: lnbits
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - LNBITS_DEFAULT_WALLET_NAME=MCP Wallet
      - LNBITS_DISABLED_EXTENSIONS=events,devicetest,watchonly,lnurlp,lnurldevice,lnurlpos,lnurlatm,lnurltxbit,lnurlwithdraw,lnurlpay
      - LNBITS_BACKEND_WALLET_CLASS=LndRestWallet
      - LNBITS_LND_REST_ENDPOINT=http://lnd:8080
      - LNBITS_LND_REST_CERT=/app/lnd/tls.cert
      - LNBITS_LND_REST_MACAROON=/app/lnd/admin.macaroon
    volumes:
      - ./data/lnbits:/app/data
      - ./lnd:/app/lnd:ro
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # LND - Lightning Network Daemon (simulateur)
  lnd:
    image: lightninglabs/lnd:latest
    container_name: lnd
    restart: unless-stopped
    ports:
      - "10009:10009"
      - "8080:8080"
    environment:
      - LND_ALIAS=MCP Node
      - LND_COLOR=#3399FF
    volumes:
      - ./data/lnd:/root/.lnd
    networks:
      - mcp-network
    command: >
      lnd
      --bitcoin.active=false
      --bitcoin.regtest=true
      --bitcoin.node=bitcoind
      --bitcoind.rpcuser=bitcoin
      --bitcoind.rpcpass=bitcoin
      --bitcoind.rpchost=bitcoind
      --bitcoind.zmqpubrawblock=tcp://bitcoind:28332
      --bitcoind.zmqpubrawtx=tcp://bitcoind:28333
      --rpclisten=0.0.0.0:10009
      --restlisten=0.0.0.0:8080
      --listen=0.0.0.0:9735
      --debuglevel=info
      --accept-keysend=true
      --accept-amp=true

  # Bitcoind - Bitcoin Core (pour LND)
  bitcoind:
    image: bitcoin/bitcoin-core:latest
    container_name: bitcoind
    restart: unless-stopped
    ports:
      - "8332:8332"
      - "28332:28332"
      - "28333:28333"
    environment:
      - BITCOIN_RPC_USER=bitcoin
      - BITCOIN_RPC_PASSWORD=bitcoin
    volumes:
      - ./data/bitcoin:/root/.bitcoin
    networks:
      - mcp-network
    command: >
      bitcoind
      -regtest=1
      -rpcuser=bitcoin
      -rpcpassword=bitcoin
      -rpcallowip=0.0.0.0/0
      -rpcbind=0.0.0.0
      -zmqpubrawblock=tcp://0.0.0.0:28332
      -zmqpubrawtx=tcp://0.0.0.0:28333
      -txindex=1
      -server=1

networks:
  mcp-network:
    driver: bridge
COMPOSE_EOF

        echo "✅ docker-compose.lnbits.yml créé"
        
        # Créer les répertoires nécessaires
        mkdir -p data/{lnbits,lnd,bitcoin}
        echo "✅ Répertoires créés"
EOF
}

# Démarrage de LNBits
demarrer_lnbits() {
    info "🚀 Démarrage de LNBits..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Arrêt des services existants ==="
        echo "Feustey@AI!" | sudo -S docker-compose down --remove-orphans || true
        
        echo "=== Démarrage de LNBits ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.lnbits.yml up -d
        
        echo "=== Attente du démarrage ==="
        sleep 60
        
        echo "=== Vérification des services ==="
        echo "Feustey@AI!" | sudo -S docker-compose -f docker-compose.lnbits.yml ps
        
        echo "=== Test de LNBits ==="
        for i in {1..10}; do
            if curl -f http://localhost:5000/api/v1/health 2>/dev/null; then
                echo "✅ LNBits accessible"
                break
            else
                echo "⏳ Tentative $i/10 - LNBits non accessible, attente..."
                sleep 15
            fi
        done
        
        echo "=== Logs LNBits ==="
        docker logs lnbits --tail=10
EOF
}

# Configuration de l'API MCP pour LNBits
configurer_mcp_lnbits() {
    info " Configuration de l'API MCP pour LNBits..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        cd /home/feustey/feustey
        
        echo "=== Mise à jour des variables d'environnement ==="
        
        # Ajouter les variables LNBits au fichier .env.production
        if [ -f ".env.production" ]; then
            # Vérifier si les variables existent déjà
            if ! grep -q "LNBITS_URL" .env.production; then
                echo "LNBITS_URL=http://lnbits:5000" >> .env.production
                echo "✅ LNBITS_URL ajoutée"
            fi
            
            if ! grep -q "LNBITS_API_KEY" .env.production; then
                echo "LNBITS_API_KEY=your_api_key_here" >> .env.production
                echo "✅ LNBITS_API_KEY ajoutée"
            fi
            
            if ! grep -q "LNBITS_ADMIN_KEY" .env.production; then
                echo "LNBITS_ADMIN_KEY=your_admin_key_here" >> .env.production
                echo "✅ LNBITS_ADMIN_KEY ajoutée"
            fi
            
            echo "=== Variables LNBits dans .env.production ==="
            grep -E "(LNBITS_URL|LNBITS_API_KEY|LNBITS_ADMIN_KEY)" .env.production || echo "Aucune variable trouvée"
        else
            echo "❌ Fichier .env.production non trouvé"
        fi
EOF
}

# Test de LNBits
test_lnbits() {
    info "🧪 Test de LNBits..."
    
    ssh $SSH_OPTIONS "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
        echo "=== Test de LNBits ==="
        
        echo "1. Test de l'API LNBits:"
        curl -f http://localhost:5000/api/v1/health && echo " ✅" || echo " ❌"
        
        echo "2. Test de l'interface web:"
        curl -f http://localhost:5000 && echo " ✅" || echo " ❌"
        
        echo "3. Test de LND:"
        curl -f http://localhost:8080/v1/getinfo && echo " ✅" || echo " ❌"
        
        echo "4. Test de Bitcoin Core:"
        curl -f --user bitcoin:bitcoin --data-binary '{"jsonrpc": "1.0", "id": "curltest", "method": "getblockchaininfo", "params": []}' -H 'content-type: text/plain;' http://localhost:8332/ && echo " ✅" || echo " ❌"
        
        echo -e "\n=== URLs d'accès ==="
        echo "🌐 LNBits Web: http://147.79.101.32:5000"
        echo "🔌 LNBits API: http://147.79.101.32:5000/api/v1/"
        echo "⚡ LND REST: http://147.79.101.32:8080"
        echo "₿ Bitcoin RPC: http://147.79.101.32:8332"
EOF
}

# Fonction principale
main() {
    echo "⚡ Déploiement de LNBits sur Hostinger"
    echo "===================================="
    
    check_connectivity
    creer_compose_lnbits
    
    read -p "Voulez-vous démarrer LNBits? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        demarrer_lnbits
        configurer_mcp_lnbits
        test_lnbits
        
        success "🎉 LNBits déployé avec succès!"
        echo ""
        echo " Prochaines étapes:"
        echo "   1. Accéder à http://147.79.101.32:5000"
        echo "   2. Créer un wallet LNBits"
        echo "   3. Récupérer les clés API et Admin"
        echo "   4. Mettre à jour .env.production avec les vraies clés"
        echo "   5. Redémarrer l'API MCP"
    else
        info "❌ Déploiement annulé"
    fi
}

# Exécution du script
main "$@" 