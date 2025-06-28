# Utilisation d'une image de base Ubuntu 22.04
FROM ubuntu:22.04

# Configuration des miroirs et installation des dépendances
RUN echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/80-retries && \
    echo "deb http://fr.archive.ubuntu.com/ubuntu/ jammy main restricted universe multiverse\n\
deb http://fr.archive.ubuntu.com/ubuntu/ jammy-updates main restricted universe multiverse\n\
deb http://fr.archive.ubuntu.com/ubuntu/ jammy-backports main restricted universe multiverse\n\
deb http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse" > /etc/apt/sources.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    cron \
    wget \
    gnupg \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Installation de MongoDB Shell et outils depuis le dépôt officiel
RUN wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - && \
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    mongodb-mongosh \
    mongodb-database-tools \
    && rm -rf /var/lib/apt/lists/*

# Installation de redis-tools
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    redis-tools \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configuration du fuseau horaire
RUN ln -snf /usr/share/zoneinfo/Europe/Paris /etc/localtime && \
    echo "Europe/Paris" > /etc/timezone

# Création des répertoires nécessaires
RUN mkdir -p /app/backups /var/log
RUN touch /var/log/cron.log

# Copie des scripts
COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
COPY cleanup.sh /usr/local/bin/cleanup.sh
COPY entrypoint.sh /entrypoint.sh
COPY crontab /etc/cron.d/backup-cron

# Attribution des permissions
RUN chmod +x /usr/local/bin/backup.sh \
    /usr/local/bin/restore.sh \
    /usr/local/bin/cleanup.sh \
    /entrypoint.sh \
    && chmod 0644 /etc/cron.d/backup-cron

# Point d'entrée
ENTRYPOINT ["/entrypoint.sh"]