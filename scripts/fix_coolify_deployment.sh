#!/bin/bash
# scripts/fix_coolify_deployment.sh - Nettoyage et redéploiement complet Coolify
# Dernière mise à jour: 7 janvier 2025

set -e

# Variables de configuration
COOLIFY_URL="https://coolify.marshmaflow.app"
API_SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"
DOMAIN="api.dazno.de"
BACKUP_DIR="backups/coolify_recovery_$(date +%Y%m%d_%H%M%S)"

echo "🚀 === RÉCUPÉRATION COOLIFY COMPLÈTE ==="
echo "======================================"

# Fonction utilitaire pour logs
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Fonction pour les erreurs
error_exit() {
    log "❌ ERREUR: $1"
    exit 1
}

# 1. DIAGNOSTIC INITIAL
log "🔍 Phase 1: Diagnostic initial..."

# Test de connectivité à Coolify
log "Test de connectivité à $COOLIFY_URL..."
if curl -s --connect-timeout 10 "$COOLIFY_URL" > /dev/null 2>&1; then
    log "✅ Coolify accessible"
    COOLIFY_ACCESSIBLE=true
else
    log "❌ Coolify non accessible"
    COOLIFY_ACCESSIBLE=false
fi

# Test de connectivité au serveur API
log "Test de connectivité au serveur $API_SERVER..."
if ping -c 3 "$API_SERVER" > /dev/null 2>&1; then
    log "✅ Serveur API accessible"
    SERVER_ACCESSIBLE=true
else
    log "❌ Serveur API non accessible"
    SERVER_ACCESSIBLE=false
fi

# 2. SAUVEGARDE PRÉVENTIVE
log "📦 Phase 2: Sauvegarde préventive..."
mkdir -p "$BACKUP_DIR"

# Sauvegarde des configurations importantes
cp -r data/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r config/ "$BACKUP_DIR/" 2>/dev/null || true
cp .env.local "$BACKUP_DIR/" 2>/dev/null || true
cp docker-compose.*.yml "$BACKUP_DIR/" 2>/dev/null || true

log "✅ Sauvegarde créée dans $BACKUP_DIR"

# 3. NETTOYAGE LOCAL
log "🧹 Phase 3: Nettoyage local..."

# Arrêt des conteneurs locaux
docker-compose -f docker-compose.coolify.yml down --remove-orphans 2>/dev/null || true
docker-compose down --remove-orphans 2>/dev/null || true

# Nettoyage des images orphelines
docker system prune -f
docker image prune -f

# Suppression des volumes inutilisés
docker volume prune -f

log "✅ Nettoyage local terminé"

# 4. RECONSTRUCTION DE L'IMAGE
log "🔨 Phase 4: Reconstruction de l'image..."

# Construction de l'image Coolify optimisée
if docker build -f Dockerfile.coolify -t mcp-api:latest .; then
    log "✅ Image construite avec succès"
else
    log "❌ Échec de construction de l'image"
    exit 1
fi

# Test rapide de l'image
if docker run --rm mcp-api:latest python -c "print('✅ Image OK')" 2>/dev/null; then
    log "✅ Image testée avec succès"
else
    log "❌ Test de l'image échoué"
fi

# 5. TENTATIVE DE REDÉPLOIEMENT
if [ "$COOLIFY_ACCESSIBLE" = true ]; then
    log "📋 Coolify accessible - instructions pour redéploiement manuel"
else
    log "⚠️ Coolify non accessible - tentative de déploiement direct"
    
    if [ "$SERVER_ACCESSIBLE" = true ]; then
        log "🔧 Phase 5: Déploiement direct sur serveur..."
        
        # Test SSH
        if sshpass -p "$SSH_PASS" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" "echo 'SSH OK'" 2>/dev/null; then
            log "✅ Connexion SSH établie"
            
            # Nettoyage distant
            sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" << 'ENDSSH'
                # Arrêt des conteneurs existants
                sudo docker stop $(sudo docker ps -q) 2>/dev/null || true
                sudo docker system prune -af
                echo "✅ Nettoyage distant terminé"
ENDSSH
            
            # Copie et déploiement de l'image
            log "📤 Copie de l'image vers le serveur..."
            docker save mcp-api:latest | gzip | sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" "gunzip | sudo docker load"
            
            # Démarrage du conteneur
            sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$API_SERVER" << 'ENDSSH'
                sudo docker run -d \
                    --name mcp-api \
                    --restart unless-stopped \
                    -p 8000:8000 \
                    -e ENVIRONMENT=production \
                    -e LOG_LEVEL=INFO \
                    -e DRY_RUN=true \
                    -e PORT=8000 \
                    mcp-api:latest
                
                echo "✅ Conteneur démarré"
                sudo docker ps
ENDSSH
            
            log "✅ Déploiement direct terminé"
        else
            log "❌ Connexion SSH échouée"
        fi
    fi
fi

# 6. VÉRIFICATION FINALE
log "🔍 Phase 6: Vérification finale..."

# Attendre le démarrage
sleep 10

# Test des endpoints
endpoints=(
    "https://$DOMAIN/health"
    "http://$API_SERVER:8000/health"
)

for endpoint in "${endpoints[@]}"; do
    log "Test $endpoint..."
    if curl -s --connect-timeout 5 "$endpoint" > /dev/null 2>&1; then
        log "✅ $endpoint accessible"
    else
        log "❌ $endpoint non accessible"
    fi
done

# 7. RAPPORT FINAL
log "📊 === RAPPORT FINAL ==="
log "Sauvegarde : $BACKUP_DIR"
log "Image Docker : mcp-api:latest"
log "État Coolify : $([ "$COOLIFY_ACCESSIBLE" = true ] && echo "✅ Accessible" || echo "❌ Non accessible")"
log "État Serveur : $([ "$SERVER_ACCESSIBLE" = true ] && echo "✅ Accessible" || echo "❌ Non accessible")"

echo ""
echo "🎯 PROCHAINES ÉTAPES :"
echo ""
echo "1. Si Coolify est accessible :"
echo "   - Connectez-vous à https://coolify.marshmaflow.app"
echo "   - Vérifiez l'état de vos déploiements"
echo "   - Forcez un redéploiement si nécessaire"
echo ""
echo "2. Si Coolify n'est pas accessible :"
echo "   - Le déploiement direct a été tenté"
echo "   - Vérifiez https://api.dazno.de/health"
echo "   - Contactez le support marshmaflow"
echo ""
echo "3. URLs à tester :"
echo "   - https://api.dazno.de/health"
echo "   - https://api.dazno.de/docs"
echo "   - https://coolify.marshmaflow.app"

echo ""
echo "✅ === RÉCUPÉRATION TERMINÉE ===" 