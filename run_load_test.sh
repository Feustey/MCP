#!/bin/bash

# Script de test de charge pour MCP Lightning
# Utilise Locust pour simuler différents scénarios de charge

set -e

echo "================================================"
echo "MCP Lightning - Test de Charge avec Locust"
echo "================================================"

# Configuration par défaut
HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-50}"
SPAWN_RATE="${SPAWN_RATE:-5}"
RUN_TIME="${RUN_TIME:-5m}"
HTML_REPORT="${HTML_REPORT:-load_test_report.html}"

# Fonction pour afficher l'aide
show_help() {
    echo "Usage: ./run_load_test.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host        URL du serveur (défaut: http://localhost:8000)"
    echo "  -u, --users       Nombre d'utilisateurs simultanés (défaut: 50)"
    echo "  -r, --rate        Taux de création d'utilisateurs/sec (défaut: 5)"
    echo "  -t, --time        Durée du test (défaut: 5m)"
    echo "  -o, --output      Fichier de rapport HTML (défaut: load_test_report.html)"
    echo "  --headless        Mode sans interface web"
    echo "  --help            Affiche cette aide"
    echo ""
    echo "Exemples:"
    echo "  # Test rapide avec 10 utilisateurs"
    echo "  ./run_load_test.sh -u 10 -t 1m"
    echo ""
    echo "  # Test de montée en charge progressive"
    echo "  ./run_load_test.sh -u 100 -r 2 -t 10m"
    echo ""
    echo "  # Test de production"
    echo "  ./run_load_test.sh -h https://api.dazno.de -u 200 -r 10 -t 30m --headless"
}

# Parser les arguments
HEADLESS=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -r|--rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        -t|--time)
            RUN_TIME="$2"
            shift 2
            ;;
        -o|--output)
            HTML_REPORT="$2"
            shift 2
            ;;
        --headless)
            HEADLESS=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Vérifier l'installation de Locust
if ! command -v locust &> /dev/null; then
    echo "❌ Locust n'est pas installé"
    echo "Installation avec: pip install locust"
    read -p "Voulez-vous l'installer maintenant? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install locust
    else
        exit 1
    fi
fi

# Vérifier que le fichier locustfile existe
if [ ! -f "locustfile.py" ]; then
    echo "❌ Fichier locustfile.py introuvable"
    exit 1
fi

# Créer le dossier de logs si nécessaire
mkdir -p logs

# Afficher la configuration
echo ""
echo "Configuration du test:"
echo "----------------------"
echo "🎯 Serveur cible: $HOST"
echo "👥 Nombre d'utilisateurs: $USERS"
echo "⚡ Taux de création: $SPAWN_RATE users/sec"
echo "⏱️  Durée du test: $RUN_TIME"
echo "📊 Rapport HTML: $HTML_REPORT"
echo "🖥️  Mode: $([ "$HEADLESS" = true ] && echo "Headless" || echo "Interface Web")"
echo ""

# Lancer le test
if [ "$HEADLESS" = true ]; then
    echo "🚀 Lancement du test en mode headless..."
    echo ""
    
    # Mode headless avec génération automatique du rapport
    locust -f locustfile.py \
           --host="$HOST" \
           --users="$USERS" \
           --spawn-rate="$SPAWN_RATE" \
           --run-time="$RUN_TIME" \
           --headless \
           --html="$HTML_REPORT" \
           --csv=locust_stats \
           --print-stats \
           --only-summary
    
    echo ""
    echo "✅ Test terminé!"
    echo "📊 Rapport disponible: $HTML_REPORT"
    
else
    echo "🚀 Lancement de l'interface web Locust..."
    echo ""
    echo "📱 Interface disponible sur: http://localhost:8089"
    echo ""
    echo "Instructions:"
    echo "1. Ouvrez http://localhost:8089 dans votre navigateur"
    echo "2. Entrez les paramètres:"
    echo "   - Number of users: $USERS"
    echo "   - Spawn rate: $SPAWN_RATE"
    echo "   - Host: $HOST"
    echo "3. Cliquez sur 'Start swarming'"
    echo "4. Appuyez sur Ctrl+C pour arrêter"
    echo ""
    
    # Mode avec interface web
    locust -f locustfile.py --host="$HOST"
fi

# Analyser les résultats si en mode headless
if [ "$HEADLESS" = true ] && [ -f "$HTML_REPORT" ]; then
    echo ""
    echo "================================================"
    echo "📈 Analyse des résultats"
    echo "================================================"
    
    # Extraire quelques métriques clés du CSV si disponible
    if [ -f "locust_stats.csv" ]; then
        echo ""
        echo "Métriques principales:"
        echo "----------------------"
        tail -n +2 locust_stats.csv | awk -F',' '{
            printf "• %s:\n", $1
            printf "  - Requêtes: %s\n", $2
            printf "  - Échecs: %s\n", $3
            printf "  - Temps médian: %sms\n", $4
            printf "  - Temps moyen: %sms\n", $5
            printf "  - RPS: %s\n\n", $11
        }' | head -n 20
    fi
    
    echo ""
    echo "💡 Recommandations basées sur le test:"
    echo "---------------------------------------"
    echo "• Si latence médiane > 200ms: Optimiser les endpoints"
    echo "• Si taux d'échec > 1%: Vérifier la stabilité"
    echo "• Si RPS < attendu: Augmenter les workers/connexions"
    echo "• Ajuster LOG_REQUEST_SAMPLE_RATE selon la charge observée"
fi

echo ""
echo "================================================"
echo "✨ Test de charge terminé"
echo "================================================"