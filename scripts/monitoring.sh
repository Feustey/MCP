#!/bin/bash
# Script de monitoring automatisé pour MCP sur api.dazno.de
# Surveillance continue des services et alertes automatiques
# 
# Auteur: MCP Team
# Version: 1.0.0
# Dernière mise à jour: 27 mai 2025
# 
# Exécution recommandée: */5 * * * * /opt/mcp/scripts/monitoring.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/mcp-monitoring.log"
ALERT_EMAIL="admin@dazno.de"
CONFIG_FILE="$PROJECT_ROOT/.env.production"

# Seuils d'alerte
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
API_RESPONSE_THRESHOLD=2000  # ms
ERROR_RATE_THRESHOLD=5      # %

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Charger les variables d'environnement
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Fichier de configuration manquant: $CONFIG_FILE"
    exit 1
fi

# Fonctions utilitaires
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Fonction d'envoi d'alertes
send_alert() {
    local severity="$1"
    local service="$2"
    local message="$3"
    local metric_value="$4"
    
    local emoji="📊"
    case $severity in
        "critical")
            emoji="🚨"
            ;;
        "warning")
            emoji="⚠️"
            ;;
        "info")
            emoji="ℹ️"
            ;;
        "recovery")
            emoji="✅"
            ;;
    esac
    
    log "ALERT" "[$severity] $service: $message"
    
    # Notification Telegram
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]] && [[ -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        local telegram_message="$emoji <b>[$severity]</b> api.dazno.de
        
<b>Service:</b> $service
<b>Message:</b> $message
<b>Valeur:</b> $metric_value
<b>Timestamp:</b> $(date '+%Y-%m-%d %H:%M:%S')"
        
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d chat_id="$TELEGRAM_CHAT_ID" \
            -d text="$telegram_message" \
            -d parse_mode="HTML" > /dev/null || warn "Échec de l'envoi Telegram"
    fi
    
    # Email d'alerte (si configuré)
    if command -v mail &> /dev/null && [[ -n "$ALERT_EMAIL" ]]; then
        echo -e "Service: $service\nMessage: $message\nValeur: $metric_value\nTimestamp: $(date)" | \
            mail -s "[$severity] Alert from api.dazno.de - $service" "$ALERT_EMAIL" || warn "Échec de l'envoi email"
    fi
}

# Vérification de l'état de l'API
check_api_health() {
    local service="API_HEALTH"
    
    info "Vérification de l'état de l'API..."
    
    local start_time=$(date +%s%N)
    local response_code
    local response_time
    local health_data
    
    # Test de santé avec timeout
    if health_data=$(timeout 10 curl -s -w "%{http_code}" -o /tmp/health_response http://localhost:8000/health 2>/dev/null); then
        response_code="${health_data: -3}"
        local end_time=$(date +%s%N)
        response_time=$(( (end_time - start_time) / 1000000 ))  # en ms
        
        if [[ "$response_code" == "200" ]]; then
            # Vérifier le contenu de la réponse
            if grep -q '"status":"healthy"' /tmp/health_response 2>/dev/null; then
                success "API opérationnelle (${response_time}ms)"
                
                # Alerte si temps de réponse élevé
                if [[ $response_time -gt $API_RESPONSE_THRESHOLD ]]; then
                    send_alert "warning" "$service" "Temps de réponse élevé" "${response_time}ms"
                fi
                
                return 0
            else
                send_alert "critical" "$service" "API retourne un statut non-healthy" "HTTP $response_code"
                return 1
            fi
        else
            send_alert "critical" "$service" "API Health Check échoué" "HTTP $response_code"
            return 1
        fi
    else
        send_alert "critical" "$service" "API inaccessible ou timeout" "Connection failed"
        return 1
    fi
}

# Vérification de MongoDB
check_mongodb() {
    local service="MONGODB"
    
    info "Vérification de MongoDB..."
    
    if docker ps | grep -q mcp-mongodb-prod; then
        # Test de connectivité
        if docker exec mcp-mongodb-prod timeout 10 mongosh \
            --eval "db.adminCommand('ping')" \
            --username "$MONGO_ROOT_USER" \
            --password "$MONGO_ROOT_PASSWORD" \
            --authenticationDatabase admin \
            --quiet mongodb://localhost:27017/mcp_prod >/dev/null 2>&1; then
            
            success "MongoDB opérationnel"
            
            # Vérifier l'espace disque de MongoDB
            local db_size=$(docker exec mcp-mongodb-prod mongosh \
                --eval "db.stats().dataSize" \
                --username "$MONGO_ROOT_USER" \
                --password "$MONGO_ROOT_PASSWORD" \
                --authenticationDatabase admin \
                --quiet mongodb://localhost:27017/mcp_prod 2>/dev/null | tail -n1)
            
            if [[ -n "$db_size" ]] && [[ "$db_size" -gt 1073741824 ]]; then  # 1GB
                local db_size_gb=$((db_size / 1073741824))
                warn "Base de données MongoDB volumineuse: ${db_size_gb}GB"
            fi
            
            return 0
        else
            send_alert "critical" "$service" "Connexion MongoDB échouée" "Connection failed"
            return 1
        fi
    else
        send_alert "critical" "$service" "Container MongoDB non démarré" "Container down"
        return 1
    fi
}

# Vérification de Redis
check_redis() {
    local service="REDIS"
    
    info "Vérification de Redis..."
    
    if docker ps | grep -q mcp-redis-prod; then
        if docker exec mcp-redis-prod timeout 5 redis-cli -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
            success "Redis opérationnel"
            
            # Vérifier l'utilisation mémoire de Redis
            local memory_usage=$(docker exec mcp-redis-prod redis-cli -a "$REDIS_PASSWORD" info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
            if [[ -n "$memory_usage" ]]; then
                info "Utilisation mémoire Redis: $memory_usage"
            fi
            
            return 0
        else
            send_alert "critical" "$service" "Connexion Redis échouée" "Connection failed"
            return 1
        fi
    else
        send_alert "critical" "$service" "Container Redis non démarré" "Container down"
        return 1
    fi
}

# Vérification des ressources système
check_system_resources() {
    local service="SYSTEM_RESOURCES"
    
    info "Vérification des ressources système..."
    
    # Vérification CPU
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if [[ -n "$cpu_usage" ]]; then
        cpu_usage=${cpu_usage%.*}  # Supprimer les décimales
        if [[ $cpu_usage -gt $CPU_THRESHOLD ]]; then
            send_alert "warning" "$service" "Utilisation CPU élevée" "${cpu_usage}%"
        else
            info "Utilisation CPU: ${cpu_usage}%"
        fi
    fi
    
    # Vérification mémoire
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ -n "$memory_usage" ]]; then
        if [[ $memory_usage -gt $MEMORY_THRESHOLD ]]; then
            send_alert "warning" "$service" "Utilisation mémoire élevée" "${memory_usage}%"
        else
            info "Utilisation mémoire: ${memory_usage}%"
        fi
    fi
    
    # Vérification espace disque
    local disk_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
    if [[ -n "$disk_usage" ]]; then
        if [[ $disk_usage -gt $DISK_THRESHOLD ]]; then
            send_alert "critical" "$service" "Espace disque critique" "${disk_usage}%"
        else
            info "Utilisation disque: ${disk_usage}%"
        fi
    fi
    
    # Vérification de la charge système
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    if [[ -n "$load_avg" ]] && [[ -n "$cpu_cores" ]]; then
        local load_ratio=$(echo "$load_avg $cpu_cores" | awk '{printf "%.1f", $1/$2}')
        if (( $(echo "$load_ratio > 1.5" | bc -l) )); then
            send_alert "warning" "$service" "Charge système élevée" "Load: $load_avg (ratio: $load_ratio)"
        fi
    fi
}

# Vérification des certificats SSL
check_ssl_certificates() {
    local service="SSL_CERTIFICATES"
    
    info "Vérification des certificats SSL..."
    
    if [[ -f "/etc/letsencrypt/live/api.dazno.de/cert.pem" ]]; then
        local expiry_date=$(openssl x509 -enddate -noout -in /etc/letsencrypt/live/api.dazno.de/cert.pem 2>/dev/null | cut -d= -f2)
        if [[ -n "$expiry_date" ]]; then
            local expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null)
            local current_epoch=$(date +%s)
            local days_left=$(( (expiry_epoch - current_epoch) / 86400 ))
            
            if [[ $days_left -lt 7 ]]; then
                send_alert "critical" "$service" "Certificat SSL expire bientôt" "Expire dans $days_left jours"
            elif [[ $days_left -lt 30 ]]; then
                send_alert "warning" "$service" "Certificat SSL expire bientôt" "Expire dans $days_left jours"
            else
                success "Certificat SSL valide (expire dans $days_left jours)"
            fi
        fi
    else
        send_alert "critical" "$service" "Certificat SSL manquant" "File not found"
    fi
}

# Vérification des services Docker
check_docker_services() {
    local service="DOCKER_SERVICES"
    
    info "Vérification des services Docker..."
    
    local required_services=(
        "mcp-api-prod"
        "mcp-mongodb-prod"
        "mcp-redis-prod"
        "mcp-prometheus-prod"
        "mcp-grafana-prod"
    )
    
    local failed_services=()
    
    for service_name in "${required_services[@]}"; do
        if ! docker ps --format "table {{.Names}}" | grep -q "^$service_name$"; then
            failed_services+=("$service_name")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        send_alert "critical" "$service" "Services Docker arrêtés" "${failed_services[*]}"
        return 1
    else
        success "Tous les services Docker sont opérationnels"
        return 0
    fi
}

# Vérification des logs d'erreur
check_error_logs() {
    local service="ERROR_LOGS"
    
    info "Vérification des logs d'erreur..."
    
    # Vérifier les erreurs récentes dans les logs de l'API
    local recent_errors=0
    if [[ -f "$PROJECT_ROOT/logs/api.log" ]]; then
        # Erreurs des 5 dernières minutes
        recent_errors=$(find "$PROJECT_ROOT/logs" -name "*.log" -mmin -5 -exec grep -c "ERROR\|CRITICAL" {} \; 2>/dev/null | awk '{sum += $1} END {print sum+0}')
        
        if [[ $recent_errors -gt 10 ]]; then
            send_alert "warning" "$service" "Nombreuses erreurs détectées" "$recent_errors erreurs en 5 min"
        elif [[ $recent_errors -gt 0 ]]; then
            info "$recent_errors erreurs récentes détectées"
        fi
    fi
    
    # Vérifier les logs Docker
    local docker_errors=$(docker logs mcp-api-prod --since 5m 2>&1 | grep -c "ERROR\|CRITICAL\|FATAL" || echo "0")
    if [[ $docker_errors -gt 5 ]]; then
        send_alert "warning" "$service" "Erreurs Docker détectées" "$docker_errors erreurs en 5 min"
    fi
}

# Vérification de Prometheus et Grafana
check_monitoring_services() {
    local service="MONITORING"
    
    info "Vérification des services de monitoring..."
    
    # Prometheus
    if ! curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
        send_alert "warning" "$service" "Prometheus inaccessible" "Health check failed"
    else
        success "Prometheus opérationnel"
    fi
    
    # Grafana
    if ! curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
        send_alert "warning" "$service" "Grafana inaccessible" "Health check failed"
    else
        success "Grafana opérationnel"
    fi
}

# Nettoyage des anciens logs
cleanup_old_logs() {
    info "Nettoyage des anciens logs..."
    
    # Rotation des logs de monitoring (garder 30 jours)
    find /var/log -name "mcp-*.log" -mtime +30 -delete 2>/dev/null || true
    
    # Nettoyage des logs Docker (garder 7 jours pour les containers)
    docker system prune -f --filter "until=168h" >/dev/null 2>&1 || true
    
    # Compression des anciens logs de l'application
    find "$PROJECT_ROOT/logs" -name "*.log" -mtime +1 -not -name "*.gz" -exec gzip {} \; 2>/dev/null || true
    find "$PROJECT_ROOT/logs" -name "*.log.gz" -mtime +7 -delete 2>/dev/null || true
}

# Fonction de récupération automatique
auto_recovery() {
    local service="$1"
    
    info "Tentative de récupération automatique pour $service..."
    
    case $service in
        "API_HEALTH")
            # Redémarrer le container API
            if docker restart mcp-api-prod >/dev/null 2>&1; then
                sleep 30
                if check_api_health; then
                    send_alert "recovery" "$service" "Récupération automatique réussie" "Container restarted"
                    return 0
                fi
            fi
            ;;
        "MONGODB")
            # Redémarrer MongoDB
            if docker restart mcp-mongodb-prod >/dev/null 2>&1; then
                sleep 60  # MongoDB prend plus de temps à démarrer
                if check_mongodb; then
                    send_alert "recovery" "$service" "Récupération automatique réussie" "Container restarted"
                    return 0
                fi
            fi
            ;;
        "REDIS")
            # Redémarrer Redis
            if docker restart mcp-redis-prod >/dev/null 2>&1; then
                sleep 15
                if check_redis; then
                    send_alert "recovery" "$service" "Récupération automatique réussie" "Container restarted"
                    return 0
                fi
            fi
            ;;
    esac
    
    return 1
}

# Fonction principale de monitoring
main() {
    info "=== DÉBUT DU MONITORING MCP ==="
    info "Timestamp: $(date)"
    info "Hostname: $(hostname)"
    
    local failed_checks=0
    local total_checks=0
    
    # Vérifications principales avec récupération automatique
    local critical_services=("API_HEALTH" "MONGODB" "REDIS")
    
    for service in "${critical_services[@]}"; do
        ((total_checks++))
        case $service in
            "API_HEALTH")
                if ! check_api_health; then
                    ((failed_checks++))
                    auto_recovery "$service" || warn "Récupération automatique échouée pour $service"
                fi
                ;;
            "MONGODB")
                if ! check_mongodb; then
                    ((failed_checks++))
                    auto_recovery "$service" || warn "Récupération automatique échouée pour $service"
                fi
                ;;
            "REDIS")
                if ! check_redis; then
                    ((failed_checks++))
                    auto_recovery "$service" || warn "Récupération automatique échouée pour $service"
                fi
                ;;
        esac
    done
    
    # Vérifications additionnelles
    ((total_checks++))
    check_system_resources
    
    ((total_checks++))
    check_ssl_certificates
    
    ((total_checks++))
    check_docker_services || ((failed_checks++))
    
    ((total_checks++))
    check_error_logs
    
    ((total_checks++))
    check_monitoring_services
    
    # Nettoyage périodique (une fois par jour)
    if [[ $(date +%H:%M) == "02:00" ]]; then
        cleanup_old_logs
    fi
    
    # Résumé
    local success_rate=$(( (total_checks - failed_checks) * 100 / total_checks ))
    
    if [[ $failed_checks -eq 0 ]]; then
        success "Tous les services sont opérationnels ($total_checks/$total_checks)"
    else
        warn "$failed_checks/$total_checks vérifications ont échoué (taux de réussite: ${success_rate}%)"
    fi
    
    info "=== FIN DU MONITORING MCP ==="
    
    return $failed_checks
}

# Gestion des signaux
cleanup_monitoring() {
    info "Arrêt du monitoring en cours..."
    exit 0
}

trap cleanup_monitoring SIGINT SIGTERM

# Point d'entrée
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 