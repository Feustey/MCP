FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Installation des dépendances système nécessaires
RUN apk add --no-cache \
    curl \
    gcc \
    musl-dev \
    python3-dev \
    linux-headers \
    rust \
    cargo

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création de l'utilisateur non-root
RUN addgroup -S appuser && adduser -S appuser -G appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "rag_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 