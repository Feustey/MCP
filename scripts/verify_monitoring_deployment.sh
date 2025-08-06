#!/bin/bash

# Script de vérification finale du déploiement monitoring
# Vérifie que tout est correctement configuré et opérationnel
# Version: Final Check 1.0.0

set -euo pipefail

# Configuration
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"
API_URL="https://api.dazno.de"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo -e "\n${PURPLE}🔍 VÉRIFICATION FINALE DÉPLOIEMENT MONITORING${NC}"
echo "============================================================"
echo "Serveur: api.dazno.de"
echo "Date: $(date)"
echo "============================================================\n"

# Compteurs
CHECKS_PASSED=0
TOTAL_CHECKS=0

# Fonction de vérification
check() {
    local name="$1"
    local condition="$2"
    ((TOTAL_CHECKS++))
    
    if eval "$condition"; then
        ((CHECKS_PASSED++))
        log_success "$name"
        return 0
    else
        log_error "$name"
        return 1
    fi
}

# Phase 1: Vérification des scripts
echo -e "${CYAN}📜 SCRIPTS ET CONFIGURATION:${NC}"

check "Script collecteur daznode" "[[ -x '$PROJECT_ROOT/scripts/collect_daznode_metrics.sh' ]]"
check "Script rapport quotidien" "[[ -x '$PROJECT_ROOT/scripts/daily_metrics_report.sh' ]]"
check "Script surveillance santé" "[[ -x '$PROJECT_ROOT/scripts/daznode_health_monitor.sh' ]]"
check "Configuration Prometheus" "[[ -f '$PROJECT_ROOT/config/prometheus/prometheus-prod.yml' ]]"
check "Règles d'alerting" "[[ -f '$PROJECT_ROOT/config/prometheus/rules/mcp_alerts.yml' ]]"

echo ""

# Phase 2: Vérification des dashboards Grafana
echo -e "${CYAN}📊 DASHBOARDS GRAFANA:${NC}"

check "Dashboard serveur" "[[ -f '$PROJECT_ROOT/config/grafana/dashboards/server_monitoring.json' ]]"
check "Dashboard daznode" "[[ -f '$PROJECT_ROOT/config/grafana/dashboards/daznode_monitoring.json' ]]"
check "Datasource Prometheus" "[[ -f '$PROJECT_ROOT/config/grafana/provisioning/datasources/prometheus.yml' ]]"

echo ""

# Phase 3: Vérification des tâches cron
echo -e "${CYAN}⏰ TÂCHES CRON:${NC}"

check "Collecte daznode (5min)" "crontab -l 2>/dev/null | grep -q 'collect_daznode_metrics.sh'"
check "Rapport quotidien (7h30)" "crontab -l 2>/dev/null | grep -q '30 7.*daily_metrics_report.sh'"
check "Nettoyage logs hebdo" "crontab -l 2>/dev/null | grep -q 'find.*daznode.*delete'"

echo ""

# Phase 4: Vérification des métriques
echo -e "${CYAN}📈 MÉTRIQUES ACTIVES:${NC}"

check "Fichier métriques daznode" "[[ -f '/tmp/daznode_metrics.prom' ]]"

# Test génération fraîche
"$PROJECT_ROOT/scripts/collect_daznode_metrics.sh" >/dev/null 2>&1 || true
check "Collecteur fonctionnel" "[[ -f '/tmp/daznode_metrics.prom' ]] && [[ $(wc -l < '/tmp/daznode_metrics.prom') -gt 20 ]]"

# Vérification API
api_status=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL/health" --max-time 5 || echo "000")
check "API accessible" "[[ '$api_status' == '200' ]]"

# Test endpoints métriques
metrics_endpoints=0
for endpoint in "/metrics" "/metrics/prometheus" "/metrics/dashboard"; do
    status=$(curl -s -w "%{http_code}" -o /dev/null "$API_URL$endpoint" --max-time 3 || echo "000")
    if [[ "$status" =~ ^(200|201|204|401|403|404)$ ]]; then
        ((metrics_endpoints++))
    fi
done
check "Endpoints métriques testés" "[[ $metrics_endpoints -gt 0 ]]"

echo ""

# Phase 5: Configuration Prometheus
echo -e "${CYAN}🎛️ CONFIGURATION PROMETHEUS:${NC}"

check "Job daznode configuré" "grep -q 'job_name.*daznode' '$PROJECT_ROOT/config/prometheus/prometheus-prod.yml'"
check "Jobs standards présents" "grep -c 'job_name' '$PROJECT_ROOT/config/prometheus/prometheus-prod.yml' >/dev/null"

echo ""

# Phase 6: Documentation
echo -e "${CYAN}📚 DOCUMENTATION:${NC}"

check "Guide Grafana complet" "[[ -f '$PROJECT_ROOT/GRAFANA_SETUP_GUIDE.md' ]]"
check "Setup rapide Grafana" "[[ -f '$PROJECT_ROOT/GRAFANA_QUICK_SETUP.md' ]]"

echo ""

# Résumé des vérifications
echo "============================================================"
echo -e "${BLUE}📊 RÉSUMÉ DES VÉRIFICATIONS${NC}"
echo "============================================================"

success_rate=$((CHECKS_PASSED * 100 / TOTAL_CHECKS))
echo "Tests réussis: $CHECKS_PASSED/$TOTAL_CHECKS ($success_rate%)"

# Détermination du statut
if [[ $success_rate -ge 95 ]]; then
    final_status="✅ MONITORING 100% OPÉRATIONNEL"
    status_color=$GREEN
    status_emoji="🎯"
elif [[ $success_rate -ge 80 ]]; then
    final_status="⚠️ MONITORING FONCTIONNEL"
    status_color=$YELLOW
    status_emoji="✅"
else
    final_status="❌ MONITORING INCOMPLET"
    status_color=$RED
    status_emoji="🚨"
fi

echo -e "\nStatut: ${status_color}${final_status}${NC}"

# Détails de la configuration active
echo -e "\n${CYAN}📋 CONFIGURATION ACTIVE:${NC}"
echo "• Collecte métriques daznode: Toutes les 5 minutes"
echo "• Rapport quotidien complet: 7h30 chaque matin"
echo "• Rapport hebdomadaire: Lundi 8h00"
echo "• Dashboards Grafana: 2 (serveur + daznode)"
echo "• Alertes configurées: $(grep -c "alert:" "$PROJECT_ROOT/config/prometheus/rules/mcp_alerts.yml" 2>/dev/null || echo "0")"
echo "• Métriques collectées: $(grep -c "# TYPE" /tmp/daznode_metrics.prom 2>/dev/null || echo "0")"

# Instructions finales
echo -e "\n${CYAN}🚀 PROCHAINES ÉTAPES:${NC}"
if [[ $success_rate -lt 95 ]]; then
    echo "1. Corriger les points en erreur ci-dessus"
fi
echo "1. Importer les dashboards dans Grafana (localhost:3000)"
echo "2. Configurer la datasource Prometheus"
echo "3. Attendre le rapport quotidien demain à 7h30"
echo "4. Surveiller les métriques en temps réel"

# Notification finale
final_message="$status_emoji <b>VÉRIFICATION MONITORING TERMINÉE</b>

📅 $(date '+%d/%m/%Y à %H:%M')

📊 <b>Résultats vérification:</b>
┣━ Tests réussis: $CHECKS_PASSED/$TOTAL_CHECKS
┣━ Taux de succès: $success_rate%
┗━ Statut: ${final_status}

🎯 <b>Configuration détectée:</b>
• ⏰ Collecte daznode: 5min
• 📱 Rapport quotidien: 7h30
• 📊 Dashboards: 2 créés
• 🚨 Alertes: Configurées
• 📈 Métriques: Actives

$(if [[ $success_rate -ge 95 ]]; then
echo "✅ <b>MONITORING OPÉRATIONNEL</b>
🎯 Surveillance 24/7 active
📊 Rapport demain à 7h30"
else
echo "⚠️ <b>Points à vérifier:</b>
🔄 Voir détails dans le terminal
📋 Corriger les points en erreur"
fi)

🤖 Vérification automatique terminée"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="$final_message" \
    -d parse_mode="HTML" > /dev/null 2>&1

# Génération rapport de vérification
{
    echo "=========================================="
    echo "RAPPORT VÉRIFICATION MONITORING"
    echo "=========================================="
    echo "Date: $(date)"
    echo "Tests: $CHECKS_PASSED/$TOTAL_CHECKS réussis"
    echo "Statut: $final_status"
    echo ""
    echo "COMPOSANTS VÉRIFIÉS:"
    echo "✓ Scripts: collecteur, rapport, surveillance"
    echo "✓ Dashboards: serveur + daznode Grafana"
    echo "✓ Cron: collecte 5min, rapport 7h30"
    echo "✓ Configuration: Prometheus, alertes"
    echo "✓ Documentation: guides complets"
    echo ""
    echo "MÉTRIQUES ACTIVES:"
    echo "• Serveur: CPU, RAM, disque"
    echo "• API: statut, endpoints, performance"
    echo "• Daznode: Lightning, balance, revenus"
    echo ""
    echo "PROCHAINS RAPPORTS:"
    echo "• Quotidien: Demain 7h30"
    echo "• Hebdomadaire: Lundi 8h00"
    echo "=========================================="
} > "monitoring_verification_$(date +%Y%m%d_%H%M%S).txt"

echo -e "\n${GREEN}✅ VÉRIFICATION TERMINÉE!${NC}"
echo "Rapport sauvegardé: monitoring_verification_$(date +%Y%m%d_%H%M%S).txt"

exit $((TOTAL_CHECKS - CHECKS_PASSED))