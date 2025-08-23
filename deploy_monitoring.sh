#!/bin/bash

# Script de déploiement pour Grafana et Morpheus
echo "🚀 Démarrage du déploiement Grafana + Morpheus..."

# Charger les variables d'environnement
if [ -f .env.production ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
    echo "✅ Variables d'environnement chargées"
else
    echo "⚠️ Fichier .env.production non trouvé"
fi

# Créer le réseau externe s'il n'existe pas
docker network create mcp-network 2>/dev/null || echo "🔗 Réseau mcp-network existe déjà"

# Démarrer les services un par un pour éviter les timeouts
echo "📊 Démarrage de Prometheus..."
docker-compose -f docker-compose.grafana-morpheus.yml up -d prometheus

echo "⏰ Attente de 10 secondes pour Prometheus..."
sleep 10

echo "📈 Démarrage de Grafana..."
docker-compose -f docker-compose.grafana-morpheus.yml up -d grafana

echo "⏰ Attente de 10 secondes pour Grafana..."
sleep 10

echo "🤖 Construction et démarrage de Morpheus..."
docker-compose -f docker-compose.grafana-morpheus.yml up -d --build morpheus

echo "⏰ Attente de 15 secondes pour Morpheus..."
sleep 15

echo "📊 Démarrage des exporters de métriques..."
docker-compose -f docker-compose.grafana-morpheus.yml up -d node-exporter cadvisor

echo "✅ Déploiement terminé !"
echo ""
echo "🔗 Services disponibles:"
echo "   - Grafana: http://localhost:3000 (admin/Kq_by8iZB4XJFvwc)"
echo "   - Prometheus: http://localhost:9090"
echo "   - Morpheus API: http://localhost:8001"
echo "   - Node Exporter: http://localhost:9100"
echo "   - cAdvisor: http://localhost:8080"
echo ""

# Vérifier l'état des services
echo "🔍 État des services:"
docker-compose -f docker-compose.grafana-morpheus.yml ps