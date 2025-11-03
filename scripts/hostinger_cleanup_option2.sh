#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

have() { command -v "$1" >/dev/null 2>&1; }

maybe_sudo() {
  if have sudo; then sudo "$@"; else "$@"; fi
}

log "MCP Hostinger Cleanup - Option 2 (safe)"

log "Snapshot avant nettoyage (disque)"
df -h || true

if have docker; then
  log "Snapshot avant nettoyage (Docker)"
  docker system df -v || true
  docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}' || true
else
  log "Docker non détecté sur ce système. Certaines étapes seront ignorées."
fi

if have docker; then
  log "Purge des conteneurs arrêtés"
  docker container prune -f || true

  log "Purge des images non utilisées"
  docker image prune -a -f || true

  log "Purge du builder cache"
  docker builder prune -a -f || true

  log "Purge des réseaux non utilisés"
  docker network prune -f || true

  log "Purge des volumes non utilisés (dangling)"
  docker volume prune -f || true

  log "Tronquage des logs Docker volumineux"
  if [ -d /var/lib/docker/containers ]; then
    maybe_sudo find /var/lib/docker/containers -type f -name '*-json.log' -printf '%p\n' -exec truncate -s 0 {} \; || true
  else
    log "/var/lib/docker/containers introuvable, étape ignorée."
  fi
fi

log "Nettoyage des journaux systemd (conservation 7 jours)"
if have journalctl; then
  maybe_sudo journalctl --vacuum-time=7d || true
else
  log "journalctl non détecté, étape ignorée."
fi

log "Nettoyage des caches de paquets"
if have apt-get; then
  maybe_sudo apt-get autoremove --purge -y || true
  maybe_sudo apt-get clean || true
fi
if have dnf; then
  maybe_sudo dnf clean all -y || true
fi
if have yum; then
  maybe_sudo yum clean all -y || true
fi
if have apk; then
  maybe_sudo rm -rf /var/cache/apk/* || true
fi
if have pacman; then
  maybe_sudo pacman -Scc --noconfirm || true
fi

log "Nettoyage des caches Python/NPM si présents"
if have pip; then pip cache purge || true; fi
if have pip3; then pip3 cache purge || true; fi
if have npm; then npm cache clean --force || true; fi
if have yarn; then yarn cache clean || true; fi

log "Snapshot après nettoyage (disque)"
df -h || true

if have docker; then
  log "Snapshot après nettoyage (Docker)"
  docker system df -v || true
fi

log "Nettoyage Option 2 terminé."


