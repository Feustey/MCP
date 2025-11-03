#!/bin/bash
# setup_log_rotation.sh
# Configuration de la rotation automatique des logs MCP

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Configuration rotation automatique des logs         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

PROJECT_DIR="/Users/stephanecourant/Documents/DAZ/MCP/MCP"

# Créer le fichier de configuration logrotate
LOGROTATE_CONFIG="/etc/logrotate.d/mcp"

echo -e "${YELLOW}📝 Création du fichier de configuration logrotate...${NC}"

cat > /tmp/mcp-logrotate.conf << EOF
# Rotation des logs MCP
# Nettoyage automatique tous les jours, conservation 7 jours

${PROJECT_DIR}/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) staff
    sharedscripts
    postrotate
        # Redémarrer l'API pour rouvrir les fichiers de logs
        docker exec mcp-api kill -USR1 1 2>/dev/null || true
    endscript
}

${PROJECT_DIR}/logs/nginx/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) staff
    sharedscripts
    postrotate
        # Recharger nginx pour rouvrir les fichiers de logs
        docker exec mcp-nginx nginx -s reopen 2>/dev/null || true
    endscript
}

${PROJECT_DIR}/logs/grafana/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $(whoami) staff
}

# Nettoyage des vieux logs de déploiement (plus de 30 jours)
${PROJECT_DIR}/logs/deploy_*.log
${PROJECT_DIR}/logs/workflow_*.log {
    monthly
    rotate 3
    compress
    missingok
    notifempty
}
EOF

echo ""
echo -e "${GREEN}✓ Configuration créée: /tmp/mcp-logrotate.conf${NC}"
echo ""
echo -e "${YELLOW}Pour activer la rotation automatique (nécessite sudo):${NC}"
echo "  sudo cp /tmp/mcp-logrotate.conf ${LOGROTATE_CONFIG}"
echo "  sudo chown root:wheel ${LOGROTATE_CONFIG}"
echo "  sudo chmod 644 ${LOGROTATE_CONFIG}"
echo ""
echo -e "${YELLOW}Test manuel de la rotation:${NC}"
echo "  sudo logrotate -d ${LOGROTATE_CONFIG}  # Dry-run"
echo "  sudo logrotate -f ${LOGROTATE_CONFIG}  # Forcer la rotation"
echo ""

# Alternative: Cron job local (sans sudo)
echo -e "${BLUE}═══ Alternative: Cron job local (sans sudo) ═══${NC}"
echo ""

CRON_SCRIPT="${PROJECT_DIR}/scripts/rotate_logs_daily.sh"

cat > "$CRON_SCRIPT" << 'EOF'
#!/bin/bash
# rotate_logs_daily.sh
# Rotation manuelle des logs (alternative à logrotate)

PROJECT_DIR="/Users/stephanecourant/Documents/DAZ/MCP/MCP"
LOGS_DIR="${PROJECT_DIR}/logs"
DATE=$(date +%Y%m%d)

# Compresser et archiver les logs de plus de 7 jours
find "$LOGS_DIR" -name "*.log" -type f -mtime +7 -exec gzip {} \;

# Supprimer les archives de plus de 30 jours
find "$LOGS_DIR" -name "*.log.gz" -type f -mtime +30 -delete

# Tronquer les logs actuels s'ils sont trop gros (> 100MB)
find "$LOGS_DIR" -name "*.log" -type f -size +100M -exec truncate -s 50M {} \;

# Supprimer les vieux logs de déploiement (garder les 10 plus récents)
cd "$LOGS_DIR"
ls -t deploy_*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
ls -t workflow_*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "[$(date)] Rotation des logs effectuée" >> "${LOGS_DIR}/rotation.log"
EOF

chmod +x "$CRON_SCRIPT"

echo -e "${GREEN}✓ Script de rotation créé: $CRON_SCRIPT${NC}"
echo ""
echo -e "${YELLOW}Pour activer le cron job quotidien (3h du matin):${NC}"
echo "  crontab -e"
echo "  # Ajouter cette ligne:"
echo "  0 3 * * * ${CRON_SCRIPT} >> ${LOGS_DIR}/rotation.log 2>&1"
echo ""

# Résumé
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Configuration terminée !                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Fichiers créés:${NC}"
echo "  • Configuration logrotate: /tmp/mcp-logrotate.conf"
echo "  • Script de rotation: $CRON_SCRIPT"
echo ""
echo -e "${YELLOW}Choisissez une méthode:${NC}"
echo "  1. Logrotate système (recommandé, nécessite sudo)"
echo "  2. Cron job local (simple, sans sudo)"
echo ""

