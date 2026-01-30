#!/usr/bin/env python3
"""
Réinitialiser Redis (from scratch) – équivalent solution 3 pour Redis.
Vide la base courante (FLUSHDB) ou toute l’instance (FLUSHALL avec --all).
Utilisable avec Redis Runway / Upstash / local.

Usage:
  export REDIS_URL="redis://..."   # ou REDIS_UPSTASH_URL
  python scripts/rebuild_redis.py

  # Sans confirmation
  python scripts/rebuild_redis.py --force

  # Vider toute l’instance Redis (toutes les DB)
  python scripts/rebuild_redis.py --force --all
"""

import os
import sys

try:
    import redis
except ImportError:
    print("❌ redis requis: pip install redis")
    sys.exit(1)


def get_redis_url() -> str:
    url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_UPSTASH_URL")
    if not url:
        print("❌ Définir REDIS_URL ou REDIS_UPSTASH_URL")
        sys.exit(1)
    return url


def main():
    force = "--force" in sys.argv or "-f" in sys.argv
    flush_all = "--all" in sys.argv
    url = get_redis_url()

    print("🚀 Réinitialisation Redis (from scratch)")
    if flush_all:
        print("   Portée: toute l’instance (FLUSHALL)")
    else:
        print("   Portée: base courante uniquement (FLUSHDB)")
    if not force:
        print("   ⚠️  Toutes les clés concernées seront supprimées.")
        r = input("   Continuer ? [y/N] ").strip().lower()
        if r != "y":
            print("   Annulé.")
            sys.exit(0)

    client = redis.from_url(url, decode_responses=True)
    try:
        client.ping()
    except redis.RedisError as e:
        print(f"❌ Connexion Redis impossible: {e}")
        sys.exit(1)

    try:
        if flush_all:
            client.flushall()
            print("\n✅ Redis: FLUSHALL exécuté (toutes les DB).")
        else:
            client.flushdb()
            print("\n✅ Redis: FLUSHDB exécuté (base courante).")
    except redis.RedisError as e:
        print(f"\n❌ Erreur Redis: {e}")
        print("   (Certains hébergeurs, ex. Upstash, désactivent FLUSHDB/FLUSHALL.)")
        sys.exit(1)

    print("🎯 Redis prêt pour MCP.")
    print("   Pour réindexer le RAG: POST /api/v1/rag/reindex (ou scripts/reindex.sh).")


if __name__ == "__main__":
    main()
