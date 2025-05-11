#!/usr/bin/env python3
"""
Script pour exécuter optimize_feustey_config.py sans la partie scan de liquidité.
"""
import asyncio
import sys
import importlib.util
import os
from pathlib import Path

# Charger le module optimize_feustey_config
spec = importlib.util.spec_from_file_location("optimize_feustey_config", "optimize_feustey_config.py")
optimize_feustey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optimize_feustey)

# Remplacer la fonction scan_popular_nodes pour qu'elle ne fasse rien
async def dummy_scan_popular_nodes(*args, **kwargs):
    print("Scan de liquidité désactivé. Passage à l'étape suivante...")
    return {}

# Remplacer la fonction dans le module
optimize_feustey.scan_popular_nodes = dummy_scan_popular_nodes

# Remplacer également la fonction evaluate_node_liquidity pour qu'elle ne fasse rien de coûteux
async def dummy_evaluate_node_liquidity(node_pubkey, test_id):
    print(f"Évaluation de liquidité désactivée pour {node_pubkey}")
    # Retourner un dictionnaire vide qui ne perturbe pas le calcul du score
    return {}

# Remplacer la fonction dans le module
optimize_feustey.evaluate_node_liquidity = dummy_evaluate_node_liquidity

# Exécuter la fonction main du module
if __name__ == "__main__":
    try:
        asyncio.run(optimize_feustey.main())
    except KeyboardInterrupt:
        print("\nProcessus interrompu par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"Erreur lors de l'exécution: {e}")
        sys.exit(1) 