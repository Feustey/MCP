#\!/bin/bash

# Script de redémarrage complet des services MCP
# A exécuter sur le serveur en root

echo "🔧 REDÉMARRAGE COMPLET DES SERVICES MCP"
echo "========================================"
echo ""

echo "1. Vérification état actuel..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2. Redémarrage de l'API MCP..."
docker restart mcp-api || docker start mcp-api
sleep 10

echo "3. Test API interne..."
curl -s -o /dev/null -w "API localhost:8000 : %{http_code}\n" http://localhost:8000/health

echo ""
echo "4. Suppression ancien nginx..."
docker stop mcp-nginx 2>/dev/null
docker rm mcp-nginx 2>/dev/null
docker stop mcp-nginx-final 2>/dev/null
docker rm mcp-nginx-final 2>/dev/null

echo "5. Création config nginx simple..."
cat > /tmp/nginx.conf << 'EOFF'
server {
    listen 80;
    server_name api.dazno.de;
    
    location / {
        proxy_pass http://172.17.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOFF

echo "6. Démarrage nouveau nginx..."
docker run -d \
  --name mcp-nginx \
  --restart unless-stopped \
  -p 80:80 \
  -p 8080:80 \
  -v /tmp/nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine

sleep 5

echo ""
echo "7. Vérification services..."
docker ps | grep -E "(mcp-api|mcp-nginx)"

echo ""
echo "8. Tests finaux..."
echo -n "API direct: "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health

echo -n "Nginx port 80: "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost/health

echo -n "Nginx port 8080: "
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/health

echo ""
echo "✅ Redémarrage terminé - Services prêts pour tests externes"
EOF < /dev/null
