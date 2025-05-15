FROM python:3.9-slim

LABEL maintainer="Token4Good <dev@token4good.com>"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Dépendances système + cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

# Copie le script de purge et donne les droits
RUN chmod +x /app/umbrel-app/purge_and_compress.sh

# Ajoute la tâche cron (tous les jours à 3h)
RUN echo "0 3 * * * /app/umbrel-app/purge_and_compress.sh >> /app/data/purge.log 2>&1" > /etc/cron.d/purge_token4good
RUN chmod 0644 /etc/cron.d/purge_token4good && crontab /etc/cron.d/purge_token4good

# Lancement supervisé : cron + app
COPY --from=python:3.9-slim /usr/bin/supervisord /usr/bin/supervisord
COPY umbrel-app/supervisord.conf /etc/supervisord.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"] 