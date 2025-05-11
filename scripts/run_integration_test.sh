#!/bin/bash

# Script pour exécuter les tests d'intégration du scheduler d'optimisation des frais
# Dernière mise à jour: 10 mai 2025

set -e  # Arrêter le script à la première erreur

# Définir les couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Variables globales
DOCKER_COMPOSE_FILE="docker-compose.test.yml"
PROMETHEUS_CONFIG="prometheus.yml"
TEST_TIMEOUT=300 # 5 minutes en secondes
TEST_SUCCESS=true

# Vérifier que les dépendances nécessaires sont installées
check_dependencies() {
    echo -e "${BLUE}${BOLD}Vérification des dépendances...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker n'est pas installé. Merci d'installer Docker.${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        if ! command -v docker compose &> /dev/null; then
            echo -e "${RED}Docker Compose n'est pas installé. Merci d'installer Docker Compose.${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Toutes les dépendances sont installées.${NC}"
}

# Créer une configuration Prometheus temporaire si elle n'existe pas
create_prometheus_config() {
    echo -e "${BLUE}${BOLD}Création de la configuration Prometheus...${NC}"
    
    if [ ! -f "$PROMETHEUS_CONFIG" ]; then
        cat > "$PROMETHEUS_CONFIG" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fee-optimizer'
    static_configs:
      - targets: ['fee-optimizer:9090']

  - job_name: 'metrics-exporter'
    static_configs:
      - targets: ['metrics-exporter:9091']
EOF
        echo -e "${GREEN}✓ Configuration Prometheus créée.${NC}"
    else
        echo -e "${YELLOW}⚠ Configuration Prometheus existante, utilisation de celle-ci.${NC}"
    fi
}

# Arrêter et nettoyer les containers existants
cleanup() {
    echo -e "${BLUE}${BOLD}Nettoyage des containers existants...${NC}"
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans
    
    echo -e "${GREEN}✓ Nettoyage terminé.${NC}"
}

# Démarrer les services pour le test
start_services() {
    echo -e "${BLUE}${BOLD}Démarrage des services...${NC}"
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    echo -e "${GREEN}✓ Services démarrés.${NC}"
}

# Vérifier que tous les services sont en bonne santé
check_services_health() {
    echo -e "${BLUE}${BOLD}Vérification de la santé des services...${NC}"
    
    local retries=10
    local wait_time=15
    
    for i in $(seq 1 $retries); do
        echo -e "${YELLOW}Essai $i/$retries...${NC}"
        
        # Vérifier Redis
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec redis redis-cli ping | grep -q "PONG"; then
            echo -e "${GREEN}✓ Redis est opérationnel.${NC}"
            redis_ok=true
        else
            echo -e "${YELLOW}⚠ Redis n'est pas encore prêt.${NC}"
            redis_ok=false
        fi
        
        # Vérifier MongoDB
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec mongodb mongosh --eval "db.runCommand({ping:1})" | grep -q '"ok" : 1'; then
            echo -e "${GREEN}✓ MongoDB est opérationnel.${NC}"
            mongo_ok=true
        else
            echo -e "${YELLOW}⚠ MongoDB n'est pas encore prêt.${NC}"
            mongo_ok=false
        fi
        
        # Vérifier LNBits
        if curl -s http://localhost:5000/health | grep -q "ok"; then
            echo -e "${GREEN}✓ LNBits est opérationnel.${NC}"
            lnbits_ok=true
        else
            echo -e "${YELLOW}⚠ LNBits n'est pas encore prêt.${NC}"
            lnbits_ok=false
        fi
        
        # Vérifier que tous les services sont prêts
        if $redis_ok && $mongo_ok && $lnbits_ok; then
            echo -e "${GREEN}${BOLD}✓ Tous les services sont opérationnels.${NC}"
            return 0
        fi
        
        # Si on n'a pas atteint le nombre max de tentatives, attendre avant de réessayer
        if [ $i -lt $retries ]; then
            echo -e "${YELLOW}Attente de $wait_time secondes avant la prochaine vérification...${NC}"
            sleep $wait_time
        fi
    done
    
    echo -e "${RED}${BOLD}✗ Échec de la vérification de santé des services après $retries tentatives.${NC}"
    return 1
}

# Exécuter le test d'optimisation des frais
run_optimization_test() {
    echo -e "${BLUE}${BOLD}Exécution du test d'optimisation des frais...${NC}"
    
    # Récupérer la clé API LNBits (exemple simplifié)
    local api_key=$(curl -s http://localhost:5000/api/v1/wallet | jq -r '.id')
    
    if [ -z "$api_key" ] || [ "$api_key" == "null" ]; then
        echo -e "${YELLOW}⚠ Impossible de récupérer une clé API LNBits, utilisation d'une clé de test.${NC}"
        api_key="replacewithvalidkey"
    else
        echo -e "${GREEN}✓ Clé API LNBits récupérée: $api_key${NC}"
    fi
    
    # Exporter la clé pour être utilisée par Docker Compose
    export LNBITS_API_KEY=$api_key
    
    # Exécuter le scheduler avec la configuration test mais SANS mocks
    echo -e "${BLUE}Exécution du scheduler en mode test...${NC}"
    docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm -e LNBITS_API_KEY=$api_key -e MCP_ENV=test fee-optimizer python scripts/fee_optimizer_scheduler.py --dry-run --run-once --no-mock-allowed
    
    # Vérifier si le test a réussi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✓ Test d'optimisation des frais réussi.${NC}"
    else
        echo -e "${RED}${BOLD}✗ Échec du test d'optimisation des frais.${NC}"
        TEST_SUCCESS=false
    fi
}

# Vérifier les métriques Prometheus
check_prometheus_metrics() {
    echo -e "${BLUE}${BOLD}Vérification des métriques Prometheus...${NC}"
    
    # Attendre que Prometheus ait eu le temps de scraper les métriques
    sleep 10
    
    # Vérifier si la métrique mcp_mock_mode_active est exposée
    local mock_metrics=$(curl -s http://localhost:9091/metrics | grep mcp_mock_mode_active)
    
    if [ -n "$mock_metrics" ]; then
        echo -e "${GREEN}✓ Métriques de mock exposées correctement:${NC}"
        echo "$mock_metrics"
        
        # Vérifier s'il y a des mocks actifs alors qu'on a spécifié --no-mock-allowed
        if echo "$mock_metrics" | grep -q '1'; then
            echo -e "${RED}${BOLD}✗ Des mocks sont actifs malgré l'option --no-mock-allowed!${NC}"
            TEST_SUCCESS=false
        else
            echo -e "${GREEN}✓ Aucun mock n'est actif, comme attendu.${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Métriques de mock non trouvées.${NC}"
    fi
}

# Fonction principale
main() {
    echo -e "${BLUE}${BOLD}=== Démarrage des tests d'intégration du scheduler d'optimisation des frais ===${NC}"
    
    # Vérifier les dépendances
    check_dependencies
    
    # Créer la configuration Prometheus
    create_prometheus_config
    
    # Nettoyer l'environnement
    cleanup
    
    # Démarrer les services
    start_services
    
    # Vérifier la santé des services
    if ! check_services_health; then
        echo -e "${RED}${BOLD}Abandon des tests en raison de problèmes avec les services.${NC}"
        cleanup
        exit 1
    fi
    
    # Exécuter le test d'optimisation
    run_optimization_test
    
    # Vérifier les métriques Prometheus
    check_prometheus_metrics
    
    # Afficher le résultat final
    if $TEST_SUCCESS; then
        echo -e "${GREEN}${BOLD}=== Tests d'intégration réussis ===${NC}"
    else
        echo -e "${RED}${BOLD}=== Échec des tests d'intégration ===${NC}"
    fi
    
    # Nettoyer (sauf si on veut inspecter manuellement)
    read -p "Voulez-vous nettoyer l'environnement de test? (o/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        cleanup
    else
        echo -e "${YELLOW}Environnement de test conservé pour inspection.${NC}"
        echo -e "${YELLOW}Pour le nettoyer manuellement, exécutez: docker-compose -f $DOCKER_COMPOSE_FILE down -v --remove-orphans${NC}"
    fi
    
    # Retourner le code de sortie
    if $TEST_SUCCESS; then
        return 0
    else
        return 1
    fi
}

# Exécuter la fonction principale
main 