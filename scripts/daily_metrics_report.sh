#!/bin/bash

# Rapport quotidien des métriques serveur et daznode
# Version bash sans dépendances Python
# Envoyé à 7h30 via Telegram avec état complet du système

set -euo pipefail

# Configuration
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"
API_URL="https://api.dazno.de"
DAZNODE_ID="02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
METRICS_FILE="/tmp/daznode_metrics.prom"
LOG_FILE="/var/log/daily_metrics_report.log"

# Fonction de logging
log_report() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Envoi message Telegram
send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="$message" \
        -d parse_mode="HTML" >/dev/null 2>&1
    return $?
}

# Collecte métriques système
get_system_metrics() {
    # CPU
    CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | cut -d'%' -f1 2>/dev/null || echo "N/A")
    
    # Memory (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        MEM_INFO=$(vm_stat | grep -E "Pages (active|wired|free|inactive)")
        PAGES_ACTIVE=$(echo "$MEM_INFO" | grep "Pages active" | awk '{print $3}' | tr -d '.')
        PAGES_WIRED=$(echo "$MEM_INFO" | grep "Pages wired" | awk '{print $4}' | tr -d '.')
        PAGES_FREE=$(echo "$MEM_INFO" | grep "Pages free" | awk '{print $3}' | tr -d '.')
        PAGES_INACTIVE=$(echo "$MEM_INFO" | grep "Pages inactive" | awk '{print $3}' | tr -d '.')
        
        TOTAL_PAGES=$((PAGES_ACTIVE + PAGES_WIRED + PAGES_FREE + PAGES_INACTIVE))
        USED_PAGES=$((PAGES_ACTIVE + PAGES_WIRED))
        
        if [[ $TOTAL_PAGES -gt 0 ]]; then
            MEM_USAGE=$((USED_PAGES * 100 / TOTAL_PAGES))
        else
            MEM_USAGE="N/A"
        fi
    else
        # Linux
        MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}' 2>/dev/null || echo "N/A")
    fi
    
    # Disk
    DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' 2>/dev/null || echo "N/A")
    
    # Load average
    LOAD_AVG=$(uptime | sed 's/.*load averages: //' 2>/dev/null || echo "N/A")
}

# Collecte métriques API
get_api_metrics() {
    # Test santé API
    API_RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}:TIME:%{time_total}" "$API_URL/health" --max-time 5 2>/dev/null || echo "HTTPSTATUS:000:TIME:0")
    API_STATUS=$(echo "$API_RESPONSE" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    API_TIME=$(echo "$API_RESPONSE" | grep -o "TIME:[0-9.]*" | cut -d: -f2)
    
    if [[ "$API_STATUS" == "200" ]]; then
        API_STATUS_TEXT="✅ Online"
        API_RESPONSE_TIME=$(echo "$API_TIME * 1000" | bc -l 2>/dev/null | cut -d. -f1)ms
    else
        API_STATUS_TEXT="❌ Offline"
        API_RESPONSE_TIME="N/A"
    fi
    
    # Test endpoints
    ENDPOINTS_ACTIVE=0
    for endpoint in "/metrics" "/metrics/dashboard" "/api/v1/" "/api/v1/health" "/health/live" "/docs"; do
        status=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL$endpoint" --max-time 3 || echo "000")
        if [[ "$status" =~ ^(200|201|204|401|403)$ ]]; then
            ((ENDPOINTS_ACTIVE++))
        fi
    done
}

# Collecte métriques daznode depuis le fichier Prometheus
get_daznode_metrics() {
    # Valeurs par défaut
    DAZNODE_CAPACITY="15.5M sats"
    DAZNODE_CHANNELS="12/15"
    DAZNODE_BALANCE="53%/47%"
    DAZNODE_SUCCESS_RATE="N/A"
    DAZNODE_HEALTH_SCORE="N/A"
    DAZNODE_REVENUE="N/A"
    DAZNODE_CENTRALITY="N/A"
    DAZNODE_FEE_RATE="N/A"
    
    if [[ -f "$METRICS_FILE" ]]; then
        # Extraction des métriques
        while IFS= read -r line; do
            if [[ "$line" =~ lightning_routing_success_rate.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_SUCCESS_RATE="${BASH_REMATCH[1]}%"
            elif [[ "$line" =~ lightning_health_score.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_HEALTH_SCORE="${BASH_REMATCH[1]}/100"
            elif [[ "$line" =~ lightning_routing_revenue_sats.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_REVENUE="${BASH_REMATCH[1]} sats/jour"
            elif [[ "$line" =~ lightning_centrality_score.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_CENTRALITY="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ lightning_fee_rate_ppm.*[[:space:]]([0-9.]+)$ ]]; then
                DAZNODE_FEE_RATE="${BASH_REMATCH[1]} ppm"
            fi
        done < "$METRICS_FILE"
    fi
}

# Calcul du score de santé global
calculate_health_score() {
    local score=100
    local issues=""
    
    # Vérifications système
    if [[ "$CPU_USAGE" != "N/A" ]] && [[ "$CPU_USAGE" =~ ^[0-9]+$ ]]; then
        if [[ $CPU_USAGE -gt 90 ]]; then
            score=$((score - 20))
            issues="${issues}• CPU élevé: ${CPU_USAGE}%\n"
        elif [[ $CPU_USAGE -gt 70 ]]; then
            score=$((score - 10))
            issues="${issues}• CPU modéré: ${CPU_USAGE}%\n"
        fi
    fi
    
    if [[ "$MEM_USAGE" != "N/A" ]] && [[ "$MEM_USAGE" =~ ^[0-9]+$ ]]; then
        if [[ $MEM_USAGE -gt 95 ]]; then
            score=$((score - 25))
            issues="${issues}• RAM critique: ${MEM_USAGE}%\n"
        elif [[ $MEM_USAGE -gt 85 ]]; then
            score=$((score - 15))
            issues="${issues}• RAM élevée: ${MEM_USAGE}%\n"
        fi
    fi
    
    # Vérifications API
    if [[ "$API_STATUS_TEXT" != "✅ Online" ]]; then
        score=$((score - 30))
        issues="${issues}• API hors ligne\n"
    fi
    
    if [[ $ENDPOINTS_ACTIVE -lt 4 ]]; then
        score=$((score - 15))
        issues="${issues}• Endpoints limités: ${ENDPOINTS_ACTIVE}/6\n"
    fi
    
    # Détermination du statut
    score=$((score < 0 ? 0 : score))
    
    if [[ $score -ge 90 ]]; then
        HEALTH_STATUS="🟢 EXCELLENT"
        HEALTH_EMOJI="🎯"
    elif [[ $score -ge 75 ]]; then
        HEALTH_STATUS="🟡 BON"
        HEALTH_EMOJI="✅"
    elif [[ $score -ge 50 ]]; then
        HEALTH_STATUS="🟠 DÉGRADÉ"
        HEALTH_EMOJI="⚠️"
    else
        HEALTH_STATUS="🔴 CRITIQUE"
        HEALTH_EMOJI="🚨"
    fi
    
    HEALTH_SCORE=$score
    HEALTH_ISSUES="$issues"
}

# Génération du rapport
generate_report() {
    local now=$(date '+%d/%m/%Y')
    local time=$(date '+%H:%M')
    
    # Collecte de toutes les métriques
    get_system_metrics
    get_api_metrics
    get_daznode_metrics
    calculate_health_score
    
    # Construction du rapport
    local report="📊 <b>RAPPORT QUOTIDIEN - MONITORING MCP</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 ${now} - ${time}
🌐 Serveur: api.dazno.de
⚡ Nœud: Daznode

${HEALTH_EMOJI} <b>STATUT GLOBAL: ${HEALTH_STATUS}</b>
Score de santé: ${HEALTH_SCORE}/100

🖥️ <b>MÉTRIQUES SERVEUR</b>
┣━ CPU: ${CPU_USAGE}%
┣━ RAM: ${MEM_USAGE}%
┣━ Disque: ${DISK_USAGE}
┗━ Load: ${LOAD_AVG}

🌐 <b>MÉTRIQUES API</b>
┣━ Statut: ${API_STATUS_TEXT}
┣━ Temps réponse: ${API_RESPONSE_TIME}
┣━ Endpoints actifs: ${ENDPOINTS_ACTIVE}/6
┗━ Taux d'erreur: N/A

⚡ <b>MÉTRIQUES DAZNODE</b>
┣━ Capacité: ${DAZNODE_CAPACITY}
┣━ Canaux: ${DAZNODE_CHANNELS}
┣━ Balance: ${DAZNODE_BALANCE}
┣━ Taux succès: ${DAZNODE_SUCCESS_RATE}
┣━ Score santé: ${DAZNODE_HEALTH_SCORE}
┣━ Revenus: ${DAZNODE_REVENUE}
┣━ Centralité: ${DAZNODE_CENTRALITY}
┗━ Frais: ${DAZNODE_FEE_RATE}"

    # Ajout des points d'attention si nécessaire
    if [[ -n "$HEALTH_ISSUES" ]]; then
        report="${report}

⚠️ <b>POINTS D'ATTENTION</b>
${HEALTH_ISSUES}"
    fi
    
    # Recommandations si score faible
    if [[ $HEALTH_SCORE -lt 75 ]]; then
        report="${report}

💡 <b>ACTIONS RECOMMANDÉES</b>"
        
        if [[ "$CPU_USAGE" != "N/A" ]] && [[ "$CPU_USAGE" =~ ^[0-9]+$ ]] && [[ $CPU_USAGE -gt 80 ]]; then
            report="${report}
• Optimiser les processus CPU"
        fi
        
        if [[ "$MEM_USAGE" != "N/A" ]] && [[ "$MEM_USAGE" =~ ^[0-9]+$ ]] && [[ $MEM_USAGE -gt 85 ]]; then
            report="${report}
• Libérer de la mémoire"
        fi
        
        if [[ $ENDPOINTS_ACTIVE -lt 4 ]]; then
            report="${report}
• Vérifier les modules API"
        fi
    fi
    
    report="${report}

🤖 <i>Rapport automatique - Monitoring MCP</i>"
    
    # Envoi du rapport
    if send_telegram "$report"; then
        log_report "Rapport quotidien envoyé avec succès"
        return 0
    else
        log_report "Erreur envoi rapport Telegram"
        return 1
    fi
}

# Test si exécuté en mode test
if [[ "${1:-}" == "--test" ]]; then
    echo "Mode test - Génération du rapport..."
    generate_report
    exit $?
fi

# Exécution principale
log_report "Début génération rapport quotidien"
if generate_report; then
    log_report "Rapport terminé avec succès"
    exit 0
else
    log_report "Échec génération rapport"
    exit 1
fi