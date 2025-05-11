#!/usr/bin/env python3
import os
import sys
import asyncio
import csv
import json
from dotenv import load_dotenv

# Pour compatibilité d'import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.redis_operations import RedisOperations

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def export_scores_to_csv(output_path="scores_export.csv"):
    redis_ops = RedisOperations(REDIS_URL)
    await redis_ops._init_redis()
    # Récupérer toutes les clés score:*
    keys = await redis_ops.redis.keys("score:*")
    rows = []
    for key in keys:
        data = await redis_ops.redis.get(key)
        if not data:
            continue
        try:
            result = json.loads(data)
            rows.append(result)
        except Exception as e:
            print(f"Erreur de parsing JSON pour {key}: {e}")
    if not rows:
        print("Aucun score trouvé dans Redis.")
        return
    # Déterminer les colonnes principales
    fieldnames = [
        "pubkey", "score", "amboss_rep", "sparkseer_cent", "sparkseer_hist", "sparkseer_fees", "lnrouter_route", "errors", "timestamp"
    ]
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # S'assurer que tous les champs sont présents
            out = {k: row.get(k, "") for k in fieldnames}
            # Sérialiser errors si c'est un dict
            if isinstance(out["errors"], dict):
                out["errors"] = json.dumps(out["errors"], ensure_ascii=False)
            writer.writerow(out)
    print(f"Export terminé : {output_path}")

if __name__ == "__main__":
    asyncio.run(export_scores_to_csv()) 