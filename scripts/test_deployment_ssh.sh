#!/bin/bash

# Script de test de connectivité réseau pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

# Variables
SERVER="147.79.101.32"
SSH_PORT=22
HTTP_PORT=80
HTTPS_PORT=443

echo "🔍 Test de connectivité réseau..."

# Test de connexion SSH (port 22)
echo "Test 1: Port SSH (22)..."
if nc -z -w5 $SERVER $SSH_PORT; then
    echo "✅ Port SSH accessible"
else
    echo "❌ Port SSH non accessible"
fi

# Test de connexion HTTP (port 80)
echo "Test 2: Port HTTP (80)..."
if nc -z -w5 $SERVER $HTTP_PORT; then
    echo "✅ Port HTTP accessible"
else
    echo "❌ Port HTTP non accessible"
fi

# Test de connexion HTTPS (port 443)
echo "Test 3: Port HTTPS (443)..."
if nc -z -w5 $SERVER $HTTPS_PORT; then
    echo "✅ Port HTTPS accessible"
else
    echo "❌ Port HTTPS non accessible"
fi

# Test de latence
echo "Test 4: Latence..."
ping -c 3 $SERVER

# Test de traceroute
echo "Test 5: Route réseau..."
traceroute $SERVER

echo "✅ Tests terminés" 