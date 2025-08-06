#!/bin/bash

# Surveillance temps réel du système MCP + Daznode
# Affiche les métriques en continu et envoie des alertes

set -euo pipefail

# Configuration
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"
API_URL="https://api.dazno.de"
METRICS_FILE="/tmp/daznode_metrics.prom"
REFRESH_INTERVAL=10

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Fonction de notification
send_alert() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="🚨 <b>ALERTE MONITORING</b>

$message

⏰ $(date '+%d/%m/%Y à %H:%M')" \
        -d parse_mode="HTML" > /dev/null 2>&1 &
}

# Collecte des métriques
get_metrics() {
    # API Status
    API_STATUS=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/health" --max-time 3 || echo "000")
    
    # Système
    if command -v top >/dev/null 2>&1; then
        CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | cut -d'%' -f1 2>/dev/null || echo "N/A")
    else
        CPU_USAGE="N/A"
    fi
    
    # Métriques daznode
    DAZNODE_SUCCESS="N/A"
    DAZNODE_HEALTH="N/A"
    DAZNODE_BALANCE="53%/47%"
    
    if [[ -f "$METRICS_FILE" ]]; then
        while IFS= read -r line; do
            if [[ "$line" =~ lightning_routing_success_rate.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_SUCCESS="${BASH_REMATCH[1]}%"
            elif [[ "$line" =~ lightning_health_score.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_HEALTH="${BASH_REMATCH[1]}/100"
            fi
        done < "$METRICS_FILE"
    fi
}

# Affichage du monitoring
display_monitoring() {
    clear
    echo -e "${CYAN}⚡ MONITORING TEMPS RÉEL - MCP DAZNODE${NC}"
    echo "============================================================"
    echo -e "🕐 $(date '+%d/%m/%Y %H:%M:%S')"
    echo ""
    
    # API Status
    if [[ "$API_STATUS" == "200" ]]; then
        echo -e "🌐 API: ${GREEN}✅ Online${NC} ($API_STATUS)"
    else
        echo -e "🌐 API: ${RED}❌ Offline${NC} ($API_STATUS)"
    fi
    
    # Système
    if [[ "$CPU_USAGE" != "N/A" ]]; then
        if [[ "${CPU_USAGE%.*}" -gt 80 ]]; then
            echo -e "💻 CPU: ${RED}$CPU_USAGE%${NC}"
        elif [[ "${CPU_USAGE%.*}" -gt 60 ]]; then
            echo -e "💻 CPU: ${YELLOW}$CPU_USAGE%${NC}"
        else
            echo -e "💻 CPU: ${GREEN}$CPU_USAGE%${NC}"
        fi
    else
        echo -e "💻 CPU: ${YELLOW}N/A${NC}"
    fi
    
    # Daznode
    echo ""
    echo -e "${BLUE}⚡ DAZNODE LIGHTNING:${NC}"
    echo -e "┣━ Balance: $DAZNODE_BALANCE"
    echo -e "┣━ Taux succès: $DAZNODE_SUCCESS"
    echo -e "┗━ Santé: $DAZNODE_HEALTH"
    
    # Collecteur status
    if [[ -f "$METRICS_FILE" ]]; then
        local file_age=$(($(date +%s) - $(stat -f %m "$METRICS_FILE" 2>/dev/null || echo "0")))
        if [[ $file_age -lt 600 ]]; then
            echo -e "📊 Collecteur: ${GREEN}✅ Actif${NC} (${file_age}s)"
        else
            echo -e "📊 Collecteur: ${YELLOW}⚠️ Ancien${NC} (${file_age}s)"
        fi
    else
        echo -e "📊 Collecteur: ${RED}❌ Inactif${NC}"
    fi
    
    echo ""
    echo "Prochain rafraîchissement dans ${REFRESH_INTERVAL}s (Ctrl+C pour arrêter)"
    echo "============================================================"
}

# Vérification des alertes
check_alerts() {
    local alerts_sent=0
    
    # API offline
    if [[ "$API_STATUS" != "200" ]] && [[ ! -f "/tmp/api_alert_sent" ]]; then
        send_alert "API MCP hors ligne (code: $API_STATUS)"
        touch "/tmp/api_alert_sent"
        ((alerts_sent++))
    elif [[ "$API_STATUS" == "200" ]] && [[ -f "/tmp/api_alert_sent" ]]; then
        rm -f "/tmp/api_alert_sent"
    fi
    
    # CPU élevé
    if [[ "$CPU_USAGE" != "N/A" ]] && [[ "${CPU_USAGE%.*}" -gt 90 ]] && [[ ! -f "/tmp/cpu_alert_sent" ]]; then
        send_alert "CPU élevé détecté: $CPU_USAGE%"
        touch "/tmp/cpu_alert_sent"
        ((alerts_sent++))
    elif [[ "$CPU_USAGE" != "N/A" ]] && [[ "${CPU_USAGE%.*}" -lt 80 ]] && [[ -f "/tmp/cpu_alert_sent" ]]; then
        rm -f "/tmp/cpu_alert_sent"
    fi
    
    # Collecteur inactif
    if [[ -f "$METRICS_FILE" ]]; then
        local file_age=$(($(date +%s) - $(stat -f %m "$METRICS_FILE" 2>/dev/null || echo "0")))
        if [[ $file_age -gt 900 ]] && [[ ! -f "/tmp/collector_alert_sent" ]]; then
            send_alert "Collecteur daznode inactif depuis ${file_age}s"
            touch "/tmp/collector_alert_sent"
            ((alerts_sent++))
        elif [[ $file_age -lt 600 ]] && [[ -f "/tmp/collector_alert_sent" ]]; then
            rm -f "/tmp/collector_alert_sent"
        fi
    fi
    
    return $alerts_sent
}

# Boucle principale
echo "🚀 Démarrage du monitoring temps réel..."
echo "Surveillance: API + Système + Daznode"
echo "Alertes: Telegram activées"
echo ""

while true; do
    get_metrics
    display_monitoring
    check_alerts
    sleep $REFRESH_INTERVAL
done
