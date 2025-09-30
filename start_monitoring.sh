#!/bin/bash
# Script de démarrage du monitoring MCP en production
# Lance le monitoring en arrière-plan avec logs

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
MONITOR_SCRIPT="monitor_production.py"
LOG_DIR="logs"
PID_FILE="$LOG_DIR/monitor.pid"
LOG_FILE="$LOG_DIR/monitor_service.log"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Crée le dossier logs si nécessaire
mkdir -p "$LOG_DIR"

# Fonction: Vérifie si le monitoring tourne déjà
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Tourne
        else
            rm -f "$PID_FILE"
            return 1  # Ne tourne pas
        fi
    fi
    return 1  # Pas de PID file
}

# Fonction: Démarre le monitoring
start_monitoring() {
    if check_running; then
        echo -e "${YELLOW}⚠️  Monitoring déjà actif (PID: $(cat $PID_FILE))${NC}"
        return 1
    fi

    echo -e "${GREEN}🚀 Démarrage du monitoring MCP...${NC}"

    # Active le virtualenv si disponible
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        echo "✅ Virtualenv activé"
    fi

    # Vérifie que le script existe
    if [ ! -f "$MONITOR_SCRIPT" ]; then
        echo -e "${RED}❌ Erreur: $MONITOR_SCRIPT non trouvé${NC}"
        exit 1
    fi

    # Lance le monitoring en arrière-plan
    nohup python3 "$MONITOR_SCRIPT" \
        --interval 60 \
        >> "$LOG_FILE" 2>&1 &

    PID=$!
    echo $PID > "$PID_FILE"

    # Attend 2 secondes et vérifie que ça tourne
    sleep 2
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Monitoring démarré avec succès (PID: $PID)${NC}"
        echo -e "📊 Logs: tail -f $LOG_FILE"
        echo -e "🛑 Stop: ./start_monitoring.sh stop"
        return 0
    else
        echo -e "${RED}❌ Échec du démarrage${NC}"
        rm -f "$PID_FILE"
        echo "Dernières lignes du log:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

# Fonction: Arrête le monitoring
stop_monitoring() {
    if ! check_running; then
        echo -e "${YELLOW}⚠️  Monitoring n'est pas actif${NC}"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    echo -e "${YELLOW}🛑 Arrêt du monitoring (PID: $PID)...${NC}"

    kill "$PID" 2>/dev/null || true

    # Attend que le process se termine
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            echo -e "${GREEN}✅ Monitoring arrêté${NC}"
            return 0
        fi
        sleep 1
    done

    # Force kill si nécessaire
    echo -e "${YELLOW}⚠️  Force kill...${NC}"
    kill -9 "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Monitoring arrêté (force)${NC}"
}

# Fonction: Status du monitoring
status_monitoring() {
    if check_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${GREEN}✅ Monitoring actif (PID: $PID)${NC}"

        # Affiche les stats du process
        echo ""
        echo "📊 Process Info:"
        ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,command 2>/dev/null || echo "Process non trouvé"

        # Dernières lignes du log
        echo ""
        echo "📝 Dernières lignes du log:"
        tail -10 "$LOG_FILE"

        return 0
    else
        echo -e "${RED}❌ Monitoring n'est pas actif${NC}"
        return 1
    fi
}

# Fonction: Restart
restart_monitoring() {
    echo "🔄 Redémarrage du monitoring..."
    stop_monitoring
    sleep 2
    start_monitoring
}

# Fonction: Logs en temps réel
logs_monitoring() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${RED}❌ Fichier de log non trouvé${NC}"
        exit 1
    fi

    echo -e "${GREEN}📊 Logs en temps réel (Ctrl+C pour quitter)${NC}"
    echo ""
    tail -f "$LOG_FILE"
}

# Menu principal
case "${1:-start}" in
    start)
        start_monitoring
        ;;
    stop)
        stop_monitoring
        ;;
    restart)
        restart_monitoring
        ;;
    status)
        status_monitoring
        ;;
    logs)
        logs_monitoring
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commandes:"
        echo "  start   - Démarre le monitoring en arrière-plan"
        echo "  stop    - Arrête le monitoring"
        echo "  restart - Redémarre le monitoring"
        echo "  status  - Affiche le statut du monitoring"
        echo "  logs    - Affiche les logs en temps réel"
        exit 1
        ;;
esac

exit $?
