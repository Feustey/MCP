#!/usr/bin/env bash
set -euo pipefail

: "${EMBED_MODEL:?}"; : "${EMBED_VERSION:?}"; : "${API_BASE:?}"
: "${REDIS_URL:?}"; : "${MONGO_URL:?}"; : "${INDEX_NAME:?}"; : "${ALIAS_NAME:?}"

echo "==> Start reindex to ${INDEX_NAME} (embed=${EMBED_MODEL}@${EMBED_VERSION})"

# 1) Build shadow index (RediSearch HNSW)
redis-cli -u "$REDIS_URL" FT.CREATE "${INDEX_NAME}" ON HASH PREFIX 1 "hv:" \
 SCHEMA uid TAG lang TAG embed_version TAG vec VECTOR HNSW 12 TYPE FLOAT32 DIM 1536 DISTANCE_METRIC COSINE

# 2) Idempotent Python: ingestion → chunk → embed → index
python3 "$(dirname "$0")/reindex.py"

# 3) Alias switch
redis-cli -u "$REDIS_URL" SET "alias:${ALIAS_NAME}" "${INDEX_NAME}"

# 4) Purge caches dépendants
redis-cli -u "$REDIS_URL" KEYS "rag:retrieval:*" | xargs -r redis-cli -u "$REDIS_URL" DEL || true
redis-cli -u "$REDIS_URL" KEYS "rag:answer:*" | xargs -r redis-cli -u "$REDIS_URL" DEL || true

echo "==> Done. Alias ${ALIAS_NAME} -> ${INDEX_NAME}"




