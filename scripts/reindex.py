import os, hashlib, json, struct
from datetime import datetime
from typing import List, Dict
from pymongo import MongoClient
import redis
import numpy as np
import requests

API_BASE = os.environ["API_BASE"]
EMBED_MODEL = os.environ["EMBED_MODEL"]
EMBED_VERSION = os.environ["EMBED_VERSION"]
INDEX_NAME = os.environ["INDEX_NAME"]
REDIS_URL = os.environ["REDIS_URL"]
MONGO_URL = os.environ["MONGO_URL"]

r = redis.from_url(REDIS_URL)
mc = MongoClient(MONGO_URL)
docs = mc.get_database().get_collection("documents")

DIM = 1536

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def float32_to_bytes(arr: List[float]) -> bytes:
    arr = np.array(arr, dtype=np.float32)
    return arr.tobytes()

def embed_batch(texts: List[str]) -> List[List[float]]:
    resp = requests.post(f"{API_BASE}/api/v1/rag/embed", json={
        "model": EMBED_MODEL,
        "texts": texts,
        "embed_version": EMBED_VERSION
    }, timeout=60)
    resp.raise_for_status()
    return resp.json()["embeddings"]

def main():
    total = 0
    for d in docs.find({}, {"_id": 0}):
        uid = d.get("uid") or sha1(d.get("content", ""))
        lang = d.get("lang", "fr")
        ts = d.get("ts") or datetime.utcnow().isoformat()
        content = d.get("content", "").strip()
        if not content:
            continue

        content_hash = sha1(content)
        cache_key = f"rag:embed:hash:{uid}"
        prev = r.get(cache_key)
        tag = "|".join([content_hash, EMBED_VERSION])
        if prev and prev.decode() == tag:
            continue

        # Simple split en gros chunks (aligné spéc fonctionnelle simplifiée)
        tokens = content.split()
        target = 800
        overlap = 120
        step = target - overlap
        chs = []
        for i in range(0, len(tokens), step):
            chs.append(" ".join(tokens[i:i+target]))
        if not chs:
            chs = [content]

        embs = embed_batch(chs)
        avg = np.mean(np.array(embs, dtype=np.float32), axis=0).astype(np.float32).tolist()

        hvkey = f"hv:{uid}"
        r.hset(hvkey, mapping={
            "uid": uid,
            "lang": lang,
            "embed_version": EMBED_VERSION,
        })
        r.hset(hvkey, "vec", float32_to_bytes(avg))

        r.set(cache_key, tag)
        total += 1

    # Assurer que l'index existe déjà (créé par reindex.sh). Rien à faire ici.
    print(f"Indexed/updated {total} documents.")

if __name__ == "__main__":
    main()




