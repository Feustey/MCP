#!/bin/bash
# scripts/quick_test_coolify.sh - Test rapide de l'état Coolify
# Dernière mise à jour: 7 janvier 2025

echo "🔍 === TEST RAPIDE COOLIFY ==="

# URLs à tester
URLS=(
    "https://coolify.marshmaflow.app"
    "https://api.dazno.de/health"
    "https://api.dazno.de/docs"
    "http://147.79.101.32:8000/health"
)

for url in "${URLS[@]}"; do
    echo -n "Test $url... "
    if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ KO"
    fi
done

# Test SSH
echo -n "Test SSH 147.79.101.32... "
if nc -z -w5 147.79.101.32 22 2>/dev/null; then
    echo "✅ OK"
else
    echo "❌ KO"
fi

echo "✅ Test terminé" 