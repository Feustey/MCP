#!/bin/bash

echo "🚨 Réparation d'urgence API api.dazno.de"

# Configuration
SERVER="feustey@147.79.101.32"
API_URL="https://api.dazno.de"

# 1. Test local
echo "Test de connectivité réseau..."
ping -c 2 147.79.101.32

# 2. Test ports
echo -e "\nTest des ports..."
nc -zv 147.79.101.32 22 2>&1 | grep -E "succeeded|open" || echo "❌ SSH (22) fermé"
nc -zv 147.79.101.32 80 2>&1 | grep -E "succeeded|open" || echo "❌ HTTP (80) fermé"  
nc -zv 147.79.101.32 443 2>&1 | grep -E "succeeded|open" || echo "❌ HTTPS (443) fermé"
nc -zv 147.79.101.32 8000 2>&1 | grep -E "succeeded|open" || echo "❌ API (8000) fermé"

# 3. Tentative de connexion SSH avec timeout court
echo -e "\n🔧 Tentative de redémarrage via SSH..."
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no $SERVER << 'EOF' 2>/dev/null
echo "Connexion SSH réussie"

# Vérifier l'état des containers
docker ps -a | grep mcp

# Redémarrer tous les services MCP
cd /home/feustey/mcp-production 2>/dev/null || cd /root/mcp-production 2>/dev/null

# Stop all
docker-compose down

# Clean restart
docker system prune -f
docker-compose up -d

# Attendre le démarrage
sleep 10

# Vérifier
docker ps | grep mcp
curl -I http://localhost:8000/docs

EOF

if [ $? -ne 0 ]; then
    echo "❌ Impossible de se connecter en SSH"
    echo ""
    echo "📋 Actions manuelles requises :"
    echo "1. Connectez-vous au serveur Hostinger : 147.79.101.32"
    echo "2. Exécutez ces commandes :"
    echo "   cd /home/feustey/mcp-production"
    echo "   docker-compose down"
    echo "   docker-compose up -d"
    echo "   docker logs mcp-api-hostinger"
    echo ""
    echo "3. Vérifiez le firewall Hostinger (port 8000, 80, 443)"
    echo "4. Vérifiez les DNS de api.dazno.de"
else
    echo "✅ Services redémarrés"
fi

# 4. Test final
echo -e "\n📊 Test final..."
curl -I --max-time 5 $API_URL/docs 2>/dev/null && echo "✅ API accessible" || echo "❌ API toujours inaccessible"