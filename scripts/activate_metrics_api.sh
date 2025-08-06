#!/bin/bash

# Activation des endpoints métriques sur l'API production
# Configure FastAPI pour exposer /metrics

echo "Configuration des endpoints métriques..."

# Les endpoints sont déjà définis dans app/routes/metrics.py
# Il faut s'assurer qu'ils sont bien importés dans le main.py

# Vérification que les routes métriques sont incluses
if grep -q "metrics" "$PROJECT_ROOT/app/main.py"; then
    echo "✓ Routes métriques déjà configurées"
else
    echo "⚠ Configuration des routes métriques requise dans app/main.py"
    echo "Ajouter: app.include_router(metrics.router, prefix='/metrics')"
fi

# Test des endpoints
echo "Test des endpoints métriques..."
for endpoint in "/" "/detailed" "/prometheus" "/dashboard" "/performance" "/redis"; do
    echo -n "Testing /metrics$endpoint: "
    status=$(curl -s -w "%{http_code}" -o /dev/null "https://api.dazno.de/metrics$endpoint" --max-time 5)
    echo "$status"
done
