#!/bin/bash

# Script d'optimisation des performances API
set -e

echo "🚀 Optimisation des performances de l'API api.dazno.de"

# 1. Configuration FastAPI optimisée
cat > app/core/performance_config.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

def configure_performance(app: FastAPI):
    """Configure performance optimizations"""
    
    # Compression GZIP
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Cache headers pour documentation statique
    @app.middleware("http")
    async def add_cache_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    # Limite de requêtes
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return app

# Configuration Uvicorn optimisée
UVICORN_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,
    "loop": "uvloop",
    "http": "httptools",
    "log_level": "warning",
    "access_log": False,
    "use_colors": False,
    "limit_concurrency": 1000,
    "limit_max_requests": 10000,
    "timeout_keep_alive": 5
}
EOF

# 2. Configuration Nginx optimisée
cat > config/nginx/api-optimized.conf << 'EOF'
upstream api_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name api.dazno.de;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/api.dazno.de.crt;
    ssl_certificate_key /etc/ssl/private/api.dazno.de.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Performance optimizations
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;
    
    # Timeouts
    proxy_connect_timeout 10s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
    send_timeout 30s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml application/json
               application/javascript;
    
    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # API Documentation avec cache
    location /docs {
        proxy_pass http://api_backend/docs;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache pour la documentation
        proxy_cache_bypass $http_upgrade;
        add_header X-Cache-Status $upstream_cache_status;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # Health check
    location /health {
        proxy_pass http://api_backend/api/v1/health;
        access_log off;
        proxy_cache_bypass 1;
    }
    
    # Default location
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 3. Configuration CDN avec Cloudflare (optionnel)
cat > config/cloudflare_optimization.md << 'EOF'
# Configuration Cloudflare pour api.dazno.de

## 1. Page Rules
- URL: api.dazno.de/docs*
  - Cache Level: Cache Everything
  - Edge Cache TTL: 1 hour
  - Browser Cache TTL: 30 minutes

- URL: api.dazno.de/api/*
  - Cache Level: Bypass
  - Security Level: High

## 2. Performance Settings
- Auto Minify: ON (JavaScript, CSS, HTML)
- Brotli: ON
- HTTP/2: ON
- HTTP/3 (with QUIC): ON
- 0-RTT Connection Resumption: ON

## 3. Caching
- Browser Cache TTL: 4 hours
- Always Online: ON
- Development Mode: OFF

## 4. Network
- WebSockets: ON
- IP Geolocation: ON
- Maximum Upload Size: 100MB

## 5. Speed > Optimization
- Image Resizing: ON
- Polish: Lossless
- WebP: ON
EOF

# 4. Script de monitoring des performances
cat > scripts/monitor_api_performance.py << 'EOF'
#!/usr/bin/env python3

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import json
from datetime import datetime

class APIPerformanceMonitor:
    def __init__(self, base_url: str = "https://api.dazno.de"):
        self.base_url = base_url
        self.endpoints = [
            "/docs",
            "/api/v1/health",
            "/api/v1/status",
            "/redoc"
        ]
        
    async def measure_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> Dict:
        """Mesure les performances d'un endpoint"""
        url = f"{self.base_url}{endpoint}"
        timings = []
        
        for _ in range(5):
            start = time.time()
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    await response.text()
                    elapsed = (time.time() - start) * 1000  # ms
                    timings.append(elapsed)
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Erreur sur {endpoint}: {e}")
                timings.append(30000)  # Timeout = 30s
        
        return {
            "endpoint": endpoint,
            "avg_ms": statistics.mean(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
            "median_ms": statistics.median(timings),
            "samples": len(timings)
        }
    
    async def run_monitoring(self):
        """Lance le monitoring complet"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.measure_endpoint(session, ep) for ep in self.endpoints]
            results = await asyncio.gather(*tasks)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "results": results,
                "summary": {
                    "total_avg_ms": statistics.mean([r["avg_ms"] for r in results]),
                    "slowest_endpoint": max(results, key=lambda x: x["avg_ms"])["endpoint"],
                    "fastest_endpoint": min(results, key=lambda x: x["avg_ms"])["endpoint"]
                }
            }
            
            print(json.dumps(report, indent=2))
            
            # Alertes si trop lent
            for result in results:
                if result["avg_ms"] > 5000:
                    print(f"⚠️ ALERTE: {result['endpoint']} très lent: {result['avg_ms']:.0f}ms")
            
            return report

if __name__ == "__main__":
    monitor = APIPerformanceMonitor()
    asyncio.run(monitor.run_monitoring())
EOF

# 5. Redis pour cache
cat > config/redis_cache.conf << 'EOF'
# Configuration Redis optimisée pour cache API
maxmemory 256mb
maxmemory-policy allkeys-lru
save ""
appendonly no
tcp-keepalive 60
timeout 300
tcp-backlog 511
databases 2

# Performance
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
replica-lazy-flush yes
EOF

# 6. Script de déploiement optimisé
cat > scripts/deploy_optimized_api.sh << 'EOF'
#!/bin/bash

echo "🚀 Déploiement API optimisée"

# Variables
SERVER="feustey@147.79.101.32"
DEPLOY_PATH="/home/feustey/mcp-production"

# 1. Test de connectivité
echo "Test de connexion au serveur..."
if ! ssh -o ConnectTimeout=10 $SERVER "echo 'Connexion OK'"; then
    echo "❌ Impossible de se connecter au serveur"
    exit 1
fi

# 2. Copie des configurations
echo "Copie des configurations optimisées..."
scp config/nginx/api-optimized.conf $SERVER:$DEPLOY_PATH/config/nginx/
scp config/redis_cache.conf $SERVER:$DEPLOY_PATH/config/
scp app/core/performance_config.py $SERVER:$DEPLOY_PATH/app/core/

# 3. Restart des services
echo "Redémarrage des services..."
ssh $SERVER << 'REMOTE'
cd /home/feustey/mcp-production

# Backup configuration actuelle
cp docker-compose.yml docker-compose.backup.yml

# Update Docker Compose avec optimisations
docker-compose down
docker-compose pull
docker-compose up -d --scale mcp-api=2

# Vérification
sleep 10
docker-compose ps
curl -I http://localhost:8000/docs

# Restart Nginx avec nouvelle config
docker-compose exec nginx nginx -s reload
REMOTE

echo "✅ Déploiement terminé"
EOF

chmod +x scripts/*.sh scripts/*.py

echo "✅ Scripts d'optimisation créés"
echo ""
echo "🎯 Actions recommandées:"
echo "1. Exécuter: ./scripts/monitor_api_performance.py pour diagnostiquer"
echo "2. Déployer: ./scripts/deploy_optimized_api.sh"
echo "3. Configurer Cloudflare selon config/cloudflare_optimization.md"
echo "4. Activer Redis cache pour les endpoints fréquents"