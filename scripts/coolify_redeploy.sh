#!/bin/bash
# scripts/coolify_redeploy.sh - Redéploiement rapide via Coolify
# Dernière mise à jour: 7 janvier 2025

set -e

echo "🚀 === REDÉPLOIEMENT RAPIDE COOLIFY ==="
echo "====================================="

# Variables
COOLIFY_URL="https://coolify.marshmaflow.app"
DOMAIN="api.dazno.de"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Nettoyage rapide
log "🧹 Nettoyage rapide des conteneurs locaux..."
docker system prune -f || true

# 2. Reconstruction de l'image
log "🔨 Reconstruction de l'image Docker..."
if docker build -f Dockerfile.coolify -t mcp-api:latest .; then
    log "✅ Image construite avec succès"
else
    log "❌ Échec de construction - vérifiez les logs"
    exit 1
fi

# 3. Test rapide de l'image
log "🧪 Test rapide de l'image..."
if docker run --rm --name test-mcp mcp-api:latest python -c "import sys; print('✅ Python OK'); sys.exit(0)" 2>/dev/null; then
    log "✅ Image testée avec succès"
else
    log "⚠️ Test de l'image échoué - mais on continue"
fi

# 4. Vérification des fichiers de configuration
log "📋 Vérification des configurations..."
if [ -f "docker-compose.coolify.yml" ]; then
    log "✅ docker-compose.coolify.yml présent"
else
    log "❌ docker-compose.coolify.yml manquant"
fi

if [ -f "Dockerfile.coolify" ]; then
    log "✅ Dockerfile.coolify présent"
else
    log "❌ Dockerfile.coolify manquant"
fi

# 5. Test de connectivité Coolify
log "🔍 Test de connectivité Coolify..."
if curl -s --connect-timeout 10 "$COOLIFY_URL" > /dev/null 2>&1; then
    log "✅ Coolify accessible"
    
    # Ouvrir Coolify dans le navigateur
    log "🌐 Ouverture de Coolify dans le navigateur..."
    open "$COOLIFY_URL" 2>/dev/null || true
    
else
    log "❌ Coolify non accessible"
    exit 1
fi

# 6. Instructions de redéploiement
log "📋 === INSTRUCTIONS DE REDÉPLOIEMENT ==="
echo ""
echo "Coolify est accessible ! Suivez ces étapes :"
echo ""
echo "1. 🌐 Accédez à : $COOLIFY_URL"
echo "2. 🔑 Connectez-vous à votre compte"
echo "3. 📂 Allez dans votre projet MCP"
echo "4. 🔄 Cliquez sur 'Force Redeploy' ou 'Restart'"
echo "5. 📊 Surveillez les logs de déploiement"
echo "6. ⚙️  Vérifiez les variables d'environnement :"
echo "   - ENVIRONMENT=production"
echo "   - LOG_LEVEL=INFO"
echo "   - DRY_RUN=true"
echo "   - PORT=8000"
echo "   - MONGO_URL=mongodb://mongodb:27017/mcp"
echo "   - REDIS_HOST=redis"
echo "   - REDIS_PORT=6379"
echo "   - AI_OPENAI_API_KEY=votre_clé"
echo "   - SECURITY_SECRET_KEY=votre_clé"
echo ""
echo "7. 🔍 Après le déploiement, testez :"
echo "   - https://api.dazno.de/health"
echo "   - https://api.dazno.de/docs"
echo ""

# 7. Attendre et tester
log "⏳ Attente de 30 secondes pour permettre le redéploiement..."
sleep 30

# 8. Test final
log "🔍 Test des endpoints..."
endpoints=(
    "https://api.dazno.de/health"
    "https://api.dazno.de/docs"
)

for endpoint in "${endpoints[@]}"; do
    log "Test $endpoint..."
    if curl -s --connect-timeout 10 "$endpoint" > /dev/null 2>&1; then
        log "✅ $endpoint accessible"
    else
        log "❌ $endpoint non accessible"
    fi
done

log "✅ === SCRIPT TERMINÉ ==="
echo ""
echo "🎯 STATUT FINAL :"
echo "- Image Docker : ✅ Construite"
echo "- Coolify : ✅ Accessible"
echo "- Action requise : Redéploiement manuel via Coolify"
echo ""
echo "Si les endpoints ne répondent toujours pas :"
echo "1. Vérifiez les logs dans Coolify"
echo "2. Redémarrez le service dans Coolify"
echo "3. Contactez le support si nécessaire" 