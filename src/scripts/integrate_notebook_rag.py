import json
import os
import sys
from typing import Dict, List, Any
from datetime import datetime

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.mongodb import get_mongodb_client
from src.embeddings.openai_embeddings import get_embeddings
from src.config import get_settings

def load_notebook_data(file_path: str) -> Dict[str, Any]:
    """Charge les données du notebook depuis le fichier JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def prepare_chunks(notebook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prépare les données du notebook en chunks pour le RAG."""
    chunks = []
    
    # Ajouter le titre comme premier chunk
    title_chunk = {
        "content": notebook_data["title"],
        "metadata": {
            "source": notebook_data["metadata"]["source"],
            "type": "title",
            "processed_at": notebook_data["metadata"]["processed_at"]
        }
    }
    chunks.append(title_chunk)
    
    # Traiter chaque section
    for i, section in enumerate(notebook_data["sections"]):
        # Créer un chunk pour le titre de la section
        if section["title"]:
            section_title_chunk = {
                "content": section["title"],
                "metadata": {
                    "source": notebook_data["metadata"]["source"],
                    "type": "section_title",
                    "level": section["level"],
                    "section_index": i,
                    "processed_at": notebook_data["metadata"]["processed_at"]
                }
            }
            chunks.append(section_title_chunk)
        
        # Créer un chunk pour le contenu de la section
        if section["content"]:
            section_content_chunk = {
                "content": section["content"],
                "metadata": {
                    "source": notebook_data["metadata"]["source"],
                    "type": "section_content",
                    "level": section["level"],
                    "section_index": i,
                    "processed_at": notebook_data["metadata"]["processed_at"]
                }
            }
            chunks.append(section_content_chunk)
    
    return chunks

def get_embeddings_for_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Génère les embeddings pour chaque chunk."""
    settings = get_settings()
    embeddings_client = get_embeddings()
    
    for chunk in chunks:
        # Générer l'embedding pour le contenu
        embedding = embeddings_client.embed_query(chunk["content"])
        chunk["embedding"] = embedding
    
    return chunks

def save_to_mongodb(chunks: List[Dict[str, Any]], collection_name: str = "notebook_chunks"):
    """Sauvegarde les chunks dans MongoDB."""
    client = get_mongodb_client()
    db = client.rag_database
    collection = db[collection_name]
    
    # Supprimer les anciens documents de la même source
    if chunks:
        source = chunks[0]["metadata"]["source"]
        collection.delete_many({"metadata.source": source})
    
    # Insérer les nouveaux documents
    if chunks:
        collection.insert_many(chunks)
    
    print(f"{len(chunks)} chunks sauvegardés dans la collection {collection_name}")

def main():
    # Chemins des fichiers
    input_file = "output/notebook_processed.json"
    
    try:
        print(f"Chargement des données du notebook depuis {input_file}...")
        notebook_data = load_notebook_data(input_file)
        
        print("Préparation des chunks pour le RAG...")
        chunks = prepare_chunks(notebook_data)
        
        print(f"Génération des embeddings pour {len(chunks)} chunks...")
        chunks_with_embeddings = get_embeddings_for_chunks(chunks)
        
        print("Sauvegarde dans MongoDB...")
        save_to_mongodb(chunks_with_embeddings)
        
        print("Intégration terminée avec succès!")
        
    except Exception as e:
        print(f"Erreur: {str(e)}")

if __name__ == "__main__":
    main() 