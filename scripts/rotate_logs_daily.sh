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
