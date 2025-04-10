import json
import os
import re
from typing import Dict, List, Any
from datetime import datetime

def process_text_file(file_path: str) -> Dict[str, Any]:
    """Traite un fichier texte et le convertit en structure JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Diviser le contenu en lignes
    lines = content.split('\n')
    
    # Initialiser la structure de données
    notebook_data = {
        "title": "",
        "sections": [],
        "metadata": {
            "source": file_path,
            "processed_at": datetime.now().isoformat()
        }
    }
    
    # Extraire le titre (première ligne)
    if lines:
        notebook_data["title"] = lines[0].strip()
    
    current_section = None
    current_content = []
    
    # Traiter les lignes restantes
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        
        # Ignorer les lignes vides
        if not line:
            continue
        
        # Détecter les titres de section (lignes se terminant par ":")
        if line.endswith(":") and not line.startswith("•"):
            # Si nous avons une section en cours, la sauvegarder
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                notebook_data["sections"].append(current_section)
                current_content = []
            
            # Créer une nouvelle section
            current_section = {
                "title": line[:-1].strip(),  # Enlever les deux points
                "level": 2,  # Niveau de titre par défaut
                "content": ""
            }
        # Détecter les sous-sections (lignes commençant par "•")
        elif line.startswith("•"):
            # Si nous avons une section en cours, la sauvegarder
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                notebook_data["sections"].append(current_section)
                current_content = []
            
            # Créer une nouvelle sous-section
            current_section = {
                "title": line[1:].strip(),  # Enlever le point
                "level": 3,  # Niveau de sous-titre
                "content": ""
            }
        # Détecter les sous-sous-sections (lignes commençant par "◦")
        elif line.startswith("◦"):
            # Si nous avons une section en cours, la sauvegarder
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                notebook_data["sections"].append(current_section)
                current_content = []
            
            # Créer une nouvelle sous-sous-section
            current_section = {
                "title": line[1:].strip(),  # Enlever le point
                "level": 4,  # Niveau de sous-sous-titre
                "content": ""
            }
        elif current_section is not None:
            # Ajouter la ligne au contenu de la section en cours
            current_content.append(line)
    
    # Ajouter la dernière section
    if current_section:
        current_section["content"] = "\n".join(current_content).strip()
        notebook_data["sections"].append(current_section)
    
    return notebook_data

def save_as_json(data: Dict[str, Any], output_file: str) -> str:
    """Sauvegarde les données au format JSON."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_file

def main():
    # Chemins des fichiers
    input_file = "output/notebook.md"
    output_file = "output/notebook_processed.json"
    
    try:
        print(f"Traitement du fichier {input_file}...")
        notebook_data = process_text_file(input_file)
        
        print("Sauvegarde au format JSON...")
        json_path = save_as_json(notebook_data, output_file)
        print(f"Fichier JSON sauvegardé: {json_path}")
        
        # Afficher un résumé
        print(f"\nRésumé:")
        print(f"- Titre: {notebook_data['title']}")
        print(f"- Nombre de sections: {len(notebook_data['sections'])}")
        
    except Exception as e:
        print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    main() 