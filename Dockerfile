# Dockerfile optimisé pour déploiement MCP sur Hostinger
# Dernière mise à jour: 7 janvier 2025

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Création de l'environnement virtuel
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installation des dépendances Python
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Installation des dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Configuration de l'application
WORKDIR /app

# Copie de l'environnement virtuel du builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copie des fichiers de l'application
COPY . /app/

# Création du script de démarrage
RUN echo '#!/bin/bash\n\
exec gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 60 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile -' > /app/start.sh && \
    chmod +x /app/start.sh

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Exposition du port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Créer utilisateur non-root pour la sécurité
RUN groupadd -r mcp && useradd -r -g mcp mcp && \
    chown -R mcp:mcp /app

USER mcp

# Point d'entrée avec tini pour une gestion correcte des signaux
ENTRYPOINT ["/usr/bin/tini", "--", "/app/start.sh"]

# Labels pour la traçabilité
LABEL maintainer="MCP Team <admin@dazno.de>"
LABEL version="1.0.0"
LABEL description="MCP Lightning Network Optimizer - Hostinger Production"
LABEL org.opencontainers.image.source="https://github.com/Feustey/MCP"
LABEL org.opencontainers.image.documentation="https://docs.dazno.de/mcp"
LABEL org.opencontainers.image.vendor="Dazno"
LABEL org.opencontainers.image.licenses="MIT" 