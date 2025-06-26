#!/bin/bash

# Script de test de l'API MCP
# Dernière mise à jour: 27 mai 2025

# Variables
DOMAIN="api.dazno.de"
SERVER="147.79.101.32"

echo "🔍 Test de l'API MCP..."

# Test 1: HTTP direct sur l'IP
echo "Test 1: HTTP sur IP..."
curl -v -k http://$SERVER/health

# Test 2: HTTPS direct sur l'IP
echo "Test 2: HTTPS sur IP..."
curl -v -k https://$SERVER/health

# Test 3: HTTP sur le domaine
echo "Test 3: HTTP sur domaine..."
curl -v -H "Host: $DOMAIN" http://$SERVER/health

# Test 4: HTTPS sur le domaine
echo "Test 4: HTTPS sur domaine..."
curl -v -H "Host: $DOMAIN" https://$SERVER/health

# Test 5: Documentation Swagger
echo "Test 5: Documentation Swagger..."
curl -v -H "Host: $DOMAIN" http://$SERVER/docs

echo "✅ Tests terminés" 