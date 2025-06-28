#!/bin/bash
# Script de test de connexion SSH pour api.dazno.de
# Dernière mise à jour: 27 mai 2025

# Variables
SERVER="147.79.101.32"
SSH_USER="feustey"
SSH_PASS="Feustey@AI!"

echo "🔍 Test de connexion SSH..."

# Test avec sshpass
echo "Test 1: sshpass avec mot de passe..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER" "echo 'Test 1 OK'"

# Test avec expect
echo "Test 2: expect avec mot de passe..."
expect << 'EOF'
spawn ssh -o StrictHostKeyChecking=no feustey@147.79.101.32
expect "password:"
send "Feustey@AI!\r"
expect "$ "
send "echo 'Test 2 OK'\r"
expect "$ "
send "exit\r"
expect eof
EOF

# Test avec clé SSH temporaire
echo "Test 3: clé SSH temporaire..."
SSH_KEY="/tmp/test_key"
ssh-keygen -t rsa -b 4096 -f "$SSH_KEY" -N "" -C "test-key"
sshpass -p "$SSH_PASS" ssh-copy-id -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SERVER"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$SERVER" "echo 'Test 3 OK'"

# Nettoyage
rm -f "$SSH_KEY" "$SSH_KEY.pub"

echo "✅ Tests terminés" 