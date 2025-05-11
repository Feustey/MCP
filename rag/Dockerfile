FROM python:3.9-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Ajout des répertoires nécessaires
COPY rag /app/rag
COPY src /app/src
COPY scripts /app/scripts
COPY config.py /app/config.py
ENV PYTHONPATH="/app:/app/src"

# Création des répertoires pour les données
RUN mkdir -p /app/data/raw/amboss \
    && mkdir -p /app/data/raw/lnrouter \
    && mkdir -p /app/data/metrics \
    && mkdir -p /app/logs \
    && mkdir -p /app/rag/RAG_assets/documents/external_data

# Script de démarrage
COPY rag/start_services.sh /app/start_services.sh
RUN chmod +x /app/start_services.sh

CMD ["/app/start_services.sh"] 