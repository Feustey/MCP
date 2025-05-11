#!/usr/bin/env python3
import subprocess
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIG ---
PUBKEY_FROM = "TON_PUBKEY_LND"  # À remplacer par la pubkey de ton nœud local
PUBKEYS_TO = [
    "034ea80f8b148c750463546bd999bf7321a0e6dfc60aaf84bd0400a2e8d376c0d5",
    "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "032eafb65801a6cfb8da47c25138aa686640aec7eff486c04e8db777cf14725864",
    "02aced13b08adcbe1e0897ad3b26e4525e1a9cdb76c86ed4aa42a518045bcb7e9f",
    "03423790614f023e3c0cdaa654a3578e919947e4c3a14bf5044e7c787ebd11af1a",
    "034d3a52b36614092f2708f7ad5ceac0cc624e696f463c8b9cba8de4827de2c8dd",
    "032870511bfa0309bab3ca1832ead69eed848a4abddbc4d50e55bb2157f9525e51",
    "02f6fa3a67cb1ae7aa5ac5c86e765e6e2324570b3d6a367dc8c72bac45a5c1743f"
]
AMOUNT_SAT = 100000  # Montant à simuler (en sats)
MAX_WORKERS = 6
OUTPUT_JSON = "bos_probe_results.json"

# --- FONCTION UTILITAIRE ---
def get_bos_probe(pubkey_from: str, pubkey_to: str, amount_sat: int = 100000):
    try:
        result = subprocess.run(
            [
                "bos", "probe",
                "--from", pubkey_from,
                "--to", pubkey_to,
                "--amount", str(amount_sat),
                "--json"
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logging.warning(f"[bos probe] Erreur pour {pubkey_to}: {result.stderr.strip()}")
            return {"pubkey": pubkey_to, "error": result.stderr.strip()}
        data = json.loads(result.stdout)
        data["pubkey"] = pubkey_to
        return data
    except Exception as e:
        logging.error(f"[bos probe] Exception pour {pubkey_to}: {e}")
        return {"pubkey": pubkey_to, "error": str(e)}

# --- BATCH PARALLÈLE ---
def batch_bos_probe(pubkey_from: str, pubkeys_to: List[str], amount_sat: int = 100000, max_workers: int = 6):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pubkey = {
            executor.submit(get_bos_probe, pubkey_from, pubkey_to, amount_sat): pubkey_to
            for pubkey_to in pubkeys_to
        }
        for future in as_completed(future_to_pubkey):
            pubkey = future_to_pubkey[future]
            try:
                result = future.result()
                results.append(result)
                logging.info(f"[bos probe] Résultat pour {pubkey}: {result}")
            except Exception as exc:
                logging.error(f"[bos probe] Exception pour {pubkey}: {exc}")
                results.append({"pubkey": pubkey, "error": str(exc)})
    return results

# --- MAIN ---
if __name__ == "__main__":
    # Optionnel : permettre de passer la pubkey source et la liste cible en argument
    if len(sys.argv) > 1:
        PUBKEY_FROM = sys.argv[1]
    if len(sys.argv) > 2:
        PUBKEYS_TO = sys.argv[2:]
    results = batch_bos_probe(PUBKEY_FROM, PUBKEYS_TO, AMOUNT_SAT, MAX_WORKERS)
    # Export JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    logging.info(f"Batch terminé. Résultats exportés dans {OUTPUT_JSON}") 