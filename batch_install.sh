#!/bin/bash
# Installation par batch pour éviter les timeouts
# Production MCP API Dependencies

echo "🚀 Installation des dépendances production par batch..."

# Batch 1: Core ML
echo "📦 Batch 1: Core ML..."
docker exec mcp-api-prod pip install --no-cache-dir \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0 \
    scipy>=1.11.0

# Batch 2: AI/NLP
echo "📦 Batch 2: AI/NLP..."
docker exec mcp-api-prod pip install --no-cache-dir \
    openai>=1.12.0 \
    tiktoken>=0.6.0

# Batch 3: Logging/Monitoring
echo "📦 Batch 3: Logging..."
docker exec mcp-api-prod pip install --no-cache-dir \
    loguru>=0.7.2 \
    rich>=13.7.0 \
    psutil>=5.9.8

# Batch 4: Security
echo "📦 Batch 4: Security..."
docker exec mcp-api-prod pip install --no-cache-dir \
    cryptography>=41.0.0 \
    bcrypt>=4.0.0

# Batch 5: HTTP/Async
echo "📦 Batch 5: HTTP/Async..."
docker exec mcp-api-prod pip install --no-cache-dir \
    aiohttp>=3.9.3 \
    requests>=2.31.0 \
    nest_asyncio>=1.6.0

# Batch 6: Utilities
echo "📦 Batch 6: Utilities..."
docker exec mcp-api-prod pip install --no-cache-dir \
    python-dateutil>=2.8.2 \
    pytz>=2024.1 \
    tenacity>=8.2.3

# Batch 7: Rate Limiting
echo "📦 Batch 7: Rate Limiting..."
docker exec mcp-api-prod pip install --no-cache-dir \
    slowapi>=0.1.9 \
    fastapi-limiter>=0.1.5

# Batch 8: Scheduling
echo "📦 Batch 8: Scheduling..."
docker exec mcp-api-prod pip install --no-cache-dir \
    APScheduler>=3.10.4 \
    schedule>=1.2.1

# Batch 9: Lightning
echo "📦 Batch 9: Lightning..."
docker exec mcp-api-prod pip install --no-cache-dir \
    lnurl>=0.5.2 \
    bolt11>=2.0.5

# Batch 10: Performance
echo "📦 Batch 10: Performance..."
docker exec mcp-api-prod pip install --no-cache-dir \
    uvloop>=0.19.0 \
    asyncio-throttle>=1.0.2 \
    gunicorn>=21.2.0

echo "✅ Installation terminée!"