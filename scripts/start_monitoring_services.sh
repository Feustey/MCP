#!/bin/bash

# Script de démarrage des services monitoring
# Lance Prometheus, Grafana et configure l'environnement

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.monitoring.yml"

echo "🚀 Démarrage des services monitoring..."

# Vérification du réseau Docker
if ! docker network inspect mcp-network >/dev/null 2>&1; then
    echo "Création du réseau Docker mcp-network..."
    docker network create mcp-network
fi

# Vérification des permissions
if [[ ! -d "$PROJECT_ROOT/config/grafana" ]]; then
    echo "Erreur: Configuration Grafana manquante"
    exit 1
fi

# Correction des permissions pour Grafana
sudo chown -R 472:472 "$PROJECT_ROOT/config/grafana" 2>/dev/null || true

# Démarrage des services
echo "Démarrage Docker Compose..."
cd "$PROJECT_ROOT"
docker-compose -f "$COMPOSE_FILE" up -d

# Attente du démarrage
echo "Attente du démarrage des services..."
sleep 30

# Vérification des services
echo "Vérification des services:"
docker-compose -f "$COMPOSE_FILE" ps

# Test des endpoints
echo "Test des endpoints:"
echo -n "Prometheus: "
curl -s -f http://localhost:9090/-/healthy >/dev/null && echo "✅ OK" || echo "❌ KO"

echo -n "Grafana: "
curl -s -f http://localhost:3000/api/health >/dev/null && echo "✅ OK" || echo "❌ KO"

echo ""
echo "✅ Services monitoring démarrés!"
echo "📊 Grafana: https://api.dazno.de/grafana/ (admin/admin123)"
echo "📈 Prometheus: https://api.dazno.de/prometheus/"
echo "🎛️ Métriques API: https://api.dazno.de/metrics"
