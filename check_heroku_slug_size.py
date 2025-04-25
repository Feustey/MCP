#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def get_size(path):
    """Calcule la taille totale d'un répertoire en Mo."""
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_size(entry.path)
    return total / (1024 * 1024)  # Convertir en Mo

def check_slug_size():
    """Vérifie la taille du slug et affiche les plus gros répertoires."""
    # Lire .slugignore
    ignored = set()
    if os.path.exists('.slugignore'):
        with open('.slugignore', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignored.add(line)

    # Calculer la taille totale sans les fichiers ignorés
    total_size = 0
    sizes = {}
    
    for item in os.listdir('.'):
        if item in ignored or any(item.startswith(i.rstrip('/')) for i in ignored):
            continue
        if os.path.isfile(item) or os.path.isdir(item):
            size = get_size(item) if os.path.isdir(item) else os.path.getsize(item) / (1024 * 1024)
            sizes[item] = size
            total_size += size

    # Afficher les résultats
    print(f"\nTaille totale estimée du slug : {total_size:.2f} Mo")
    print(f"Limite Heroku : 500 Mo\n")
    
    print("Plus gros répertoires/fichiers :")
    for item, size in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{item}: {size:.2f} Mo")

    if total_size > 500:
        print(f"\n⚠️  ATTENTION: La taille du slug ({total_size:.2f} Mo) dépasse la limite de 500 Mo!")
        sys.exit(1)
    else:
        print(f"\n✅ La taille du slug est dans les limites acceptables.")

if __name__ == '__main__':
    check_slug_size() 