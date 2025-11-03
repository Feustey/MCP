#!/bin/bash
# cleanup_production_logs.sh
# Nettoyage complet des logs pour libérer de l'espace disque

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Nettoyage des logs de production                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Afficher l'espace disque avant
echo -e "${YELLOW}📊 Espace disque AVANT nettoyage:${NC}"
df -h / | head -2
echo ""

# 1. Arrêter les services pour libérer les fichiers logs
echo -e "${BLUE}═══ Arrêt des services Docker ═══${NC}"
if [ -f docker-compose.hostinger.yml ]; then
    docker-compose -f docker-compose.hostinger.yml down 2>/dev/null || echo "Services déjà arrêtés"
fi
if [ -f docker-compose.hostinger-production.yml ]; then
    docker-compose -f docker-compose.hostinger-production.yml down 2>/dev/null || echo "Services déjà arrêtés"
fi
echo -e "${GREEN}✓ Services arrêtés${NC}"
echo ""

# 2. Nettoyer les logs locaux
echo -e "${BLUE}═══ Nettoyage des logs locaux ═══${NC}"

# Logs nginx locaux
if [ -d logs/nginx ]; then
    echo "🗑️  Logs nginx locaux..."
    SIZE_BEFORE=$(du -sh logs/nginx 2>/dev/null | cut -f1)
    rm -f logs/nginx/access.log* logs/nginx/error.log* 2>/dev/null || true
    touch logs/nginx/access.log logs/nginx/error.log
    echo -e "${GREEN}✓ Logs nginx nettoyés (était: $SIZE_BEFORE)${NC}"
fi

# Logs de déploiement (garder les 3 plus récents)
echo "🗑️  Logs de déploiement..."
cd logs
COUNT_DEPLOY=$(ls deploy_*.log 2>/dev/null | wc -l || echo 0)
COUNT_WORKFLOW=$(ls workflow_*.log 2>/dev/null | wc -l || echo 0)
ls -t deploy_*.log 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
ls -t deploy_rag_*.log 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
ls -t workflow_*.log 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
ls -t ssl_setup_*.log 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
cd ..
echo -e "${GREEN}✓ Vieux logs de déploiement supprimés ($COUNT_DEPLOY deploy, $COUNT_WORKFLOW workflow)${NC}"

# Logs applicatifs (vider mais garder les fichiers)
echo "🗑️  Logs applicatifs..."
SIZE_API=$(du -sh logs/api.log 2>/dev/null | cut -f1 || echo "0K")
SIZE_MCP=$(du -sh logs/mcp.log 2>/dev/null | cut -f1 || echo "0K")
truncate -s 0 logs/api.log 2>/dev/null || true
truncate -s 0 logs/fee_optimizer.log 2>/dev/null || true
truncate -s 0 logs/mcp.log 2>/dev/null || true
truncate -s 0 logs/mcp_production.log 2>/dev/null || true
truncate -s 0 logs/mcp_monitoring.log 2>/dev/null || true
truncate -s 0 logs/monitoring.log 2>/dev/null || true
truncate -s 0 logs/node_scanner.log 2>/dev/null || true
truncate -s 0 logs/node_scanner_cron.log 2>/dev/null || true
truncate -s 0 logs/optimizer.log 2>/dev/null || true
truncate -s 0 logs/pytest.log 2>/dev/null || true
truncate -s 0 logs/rag_asset_generation.log 2>/dev/null || true
truncate -s 0 logs/stress_test.log 2>/dev/null || true
truncate -s 0 logs/monitor_service.log 2>/dev/null || true
truncate -s 0 logs/monitor-telegram-bot.log 2>/dev/null || true
truncate -s 0 logs/node_simulator.log 2>/dev/null || true
rm -f logs/mcp.log.* 2>/dev/null || true
echo -e "${GREEN}✓ Logs applicatifs vidés (api.log: $SIZE_API, mcp.log: $SIZE_MCP)${NC}"

# Logs Grafana
if [ -d logs/grafana ]; then
    echo "🗑️  Logs Grafana..."
    truncate -s 0 logs/grafana/grafana.log 2>/dev/null || true
    echo -e "${GREEN}✓ Logs Grafana nettoyés${NC}"
fi

# Logs sous-répertoires
if [ -d logs/mcp ]; then
    echo "🗑️  Logs MCP (sous-dossier)..."
    find logs/mcp -type f -name "*.log" -exec truncate -s 0 {} \; 2>/dev/null || true
    echo -e "${GREEN}✓ Logs MCP nettoyés${NC}"
fi

if [ -d logs/morpheus ]; then
    echo "🗑️  Logs Morpheus..."
    find logs/morpheus -type f -name "*.log" -exec truncate -s 0 {} \; 2>/dev/null || true
    echo -e "${GREEN}✓ Logs Morpheus nettoyés${NC}"
fi

if [ -d logs/t4g ]; then
    echo "🗑️  Logs T4G..."
    find logs/t4g -type f -name "*.log" -exec truncate -s 0 {} \; 2>/dev/null || true
    echo -e "${GREEN}✓ Logs T4G nettoyés${NC}"
fi

echo ""

# 3. Nettoyer les volumes Docker
echo -e "${BLUE}═══ Nettoyage Docker ═══${NC}"

# Logs des conteneurs Docker
echo "🗑️  Logs des conteneurs Docker..."
CLEANED=0
for container in $(docker ps -aq 2>/dev/null); do
    LOG_PATH=$(docker inspect --format='{{.LogPath}}' "$container" 2>/dev/null || echo "")
    if [ -n "$LOG_PATH" ] && [ -f "$LOG_PATH" ]; then
        SIZE=$(du -sh "$LOG_PATH" 2>/dev/null | cut -f1 || echo "0K")
        if [ "$SIZE" != "0K" ]; then
            truncate -s 0 "$LOG_PATH" 2>/dev/null || true
            CLEANED=$((CLEANED + 1))
        fi
    fi
done
echo -e "${GREEN}✓ Logs de $CLEANED conteneurs nettoyés${NC}"

# Nettoyer images et volumes inutilisés
echo "🗑️  Nettoyage Docker système..."
docker system prune -f --volumes 2>/dev/null || true
echo -e "${GREEN}✓ Système Docker nettoyé${NC}"

echo ""

# 4. Résumé de l'espace libéré
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Nettoyage terminé !                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Espace disque APRÈS nettoyage:${NC}"
df -h / | head -2
echo ""

echo -e "${GREEN}✅ Tous les logs ont été nettoyés${NC}"
echo ""
echo -e "${BLUE}📝 Prochaines étapes:${NC}"
echo "  1. Redémarrer les services:"
echo "     docker-compose -f docker-compose.hostinger.yml up -d"
echo ""
echo "  2. Optionnel - Configurer la rotation automatique des logs"
echo ""

