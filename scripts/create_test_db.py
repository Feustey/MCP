from pymongo import MongoClient
import os
from dotenv import load_dotenv

def copy_database():
    # Chargement des variables d'environnement
    load_dotenv()
    
    # Connexion à MongoDB Atlas
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise ValueError("MONGODB_URI n'est pas définie dans les variables d'environnement")
    
    print(f"Connexion à MongoDB avec l'URI: {uri}")
    client = MongoClient(uri)
    
    try:
        # Récupération des bases de données
        source_db = client.get_database("dazlng")
        target_db = client.get_database("daztest")
        
        # Liste des collections à copier
        collections = source_db.list_collection_names()
        
        print("Début de la copie des collections...")
        
        # Copie de chaque collection
        for collection_name in collections:
            print(f"Copie de la collection {collection_name}...")
            
            # Récupération des documents de la collection source
            source_collection = source_db[collection_name]
            target_collection = target_db[collection_name]
            
            # Suppression des documents existants dans la collection cible
            target_collection.delete_many({})
            
            # Copie des documents
            documents = list(source_collection.find())
            if documents:
                target_collection.insert_many(documents)
            
            print(f"Collection {collection_name} copiée avec succès")
        
        print("Copie terminée avec succès!")
        
    except Exception as e:
        print(f"Erreur lors de la copie: {str(e)}")
        raise
    finally:
        # Fermeture de la connexion
        client.close()

if __name__ == "__main__":
    copy_database() 