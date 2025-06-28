FROM alpine:3.18

# Installation des outils nécessaires
RUN apk add --no-cache \
    mongodb-tools \
    redis \
    curl \
    tar \
    gzip \
    bash \
    cronie \
    tzdata

# Configuration du timezone
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copie des scripts de sauvegarde
COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
COPY cleanup.sh /usr/local/bin/cleanup.sh

# Permissions d'exécution
RUN chmod +x /usr/local/bin/*.sh

# Configuration du cron
COPY crontab /etc/crontabs/root

# Point d'entrée
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"] 