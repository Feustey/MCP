#!/usr/bin/env python3
"""
Script pour refactoriser les imports de LNbits dans le module lnbits_internal.
Ce script remplace les imports "from lnbits" par "from lnbits_internal" dans tous les fichiers du dossier lnbits_internal.
"""

import os
import re
from pathlib import Path

def refactor_imports(directory):
    """
    Parcourt récursivement le répertoire et refactorise les imports.
    """
    print(f"Refactorisation des imports dans {directory}...")
    
    # Liste tous les fichiers Python
    py_files = list(Path(directory).glob('**/*.py'))
    total_files = len(py_files)
    modified_files = 0
    
    for file_path in py_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remplacer les imports
        new_content = re.sub(
            r'(from|import) lnbits\.', 
            r'\1 lnbits_internal.', 
            content
        )
        
        # Si le contenu a été modifié, écrire le fichier
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            modified_files += 1
            print(f"Modifié: {file_path}")
    
    print(f"Terminé! {modified_files}/{total_files} fichiers modifiés.")

if __name__ == "__main__":
    lnbits_internal_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lnbits_internal")
    refactor_imports(lnbits_internal_dir) 