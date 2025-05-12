#!/bin/bash
# Script de purge et compression pour Token4Good (Umbrel)

DATA_DIR="/app/data"
ARCHIVE_DIR="/app/data/archive"
mkdir -p "$ARCHIVE_DIR"

# Compression des fichiers de plus de 7 jours (chaud → tiède)
find $DATA_DIR -type f -mtime +7 -mtime -90 -exec gzip {} \;

# Archivage des fichiers de plus de 90 jours (tiède → froid)
find $DATA_DIR -type f -mtime +90 -exec tar -rvf $ARCHIVE_DIR/data_$(date +%Y%m%d).tar {} \; -exec rm {} \;

# Suppression des archives de plus de 1 an
find $ARCHIVE_DIR -type f -mtime +365 -delete

# Log de l'opération
NOW=$(date '+%Y-%m-%d %H:%M:%S')
echo "$NOW - Purge et compression terminées dans $DATA_DIR" >> $DATA_DIR/purge.log 