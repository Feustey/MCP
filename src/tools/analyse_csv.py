#!/usr/bin/env python3
import csv
import os
import sys
import json
from collections import Counter, defaultdict

CSV_PATH = "scores_export.csv"

if not os.path.exists(CSV_PATH):
    print(f"Fichier {CSV_PATH} introuvable.")
    sys.exit(1)

scores = []
errors = []
error_types = Counter()
score_bins = defaultdict(int)

with open(CSV_PATH, newline="") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        score = row.get("score")
        err = row.get("errors")
        if score and score not in ("", "null", None):
            try:
                s = float(score)
                scores.append(s)
                # Binning
                bin_idx = int(s * 5)  # 0-0.2, 0.2-0.4, ...
                score_bins[bin_idx] += 1
            except Exception:
                errors.append(row)
        else:
            errors.append(row)
            # Compter les types d'erreur si possible
            try:
                if err and err not in ("", "null", None):
                    err_dict = json.loads(err)
                    for k in err_dict:
                        error_types[k] += 1
            except Exception:
                error_types["parse_error"] += 1

# Statistiques
n_total = len(scores) + len(errors)
n_valid = len(scores)
n_errors = len(errors)

if scores:
    mean = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)
    std = (sum((x - mean) ** 2 for x in scores) / len(scores)) ** 0.5
else:
    mean = min_score = max_score = std = 0

print(f"Analyse du fichier {CSV_PATH}")
print(f"Total de lignes : {n_total}")
print(f"Scores valides  : {n_valid}")
print(f"Erreurs         : {n_errors}")
if n_valid:
    print(f"Score moyen     : {mean:.3f}")
    print(f"Score min/max   : {min_score:.3f} / {max_score:.3f}")
    print(f"Écart-type      : {std:.3f}")
    print("Distribution des scores :")
    for i in range(5):
        print(f"  {i*0.2:.1f}-{(i+1)*0.2:.1f} : {score_bins[i]}")
if n_errors:
    print("Types d'erreurs rencontrés :")
    for k, v in error_types.items():
        print(f"  {k} : {v}") 