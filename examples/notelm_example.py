import asyncio
from src.clients.notelm_client import NotelmClient
from src.config import get_settings

async def main():
    # Récupérer les paramètres de configuration
    settings = get_settings()
    
    # Créer une instance du client Notelm
    client = NotelmClient(
        api_key=settings.notelm_api_key,
        base_url=settings.notelm_base_url
    )
    
    try:
        # Récupérer toutes les notes
        print("Récupération de toutes les notes...")
        notes = await client.get_notes()
        print(f"Nombre de notes trouvées : {len(notes)}")
        
        # Créer une nouvelle note
        print("\nCréation d'une nouvelle note...")
        new_note = await client.create_note(
            title="Ma première note",
            content="Contenu de ma première note"
        )
        print(f"Note créée : {new_note}")
        
        # Mettre à jour la note
        print("\nMise à jour de la note...")
        updated_note = await client.update_note(
            note_id=new_note.id,
            title="Note mise à jour",
            content="Contenu mis à jour"
        )
        print(f"Note mise à jour : {updated_note}")
        
        # Récupérer une note spécifique
        print("\nRécupération de la note par ID...")
        retrieved_note = await client.get_note(new_note.id)
        print(f"Note récupérée : {retrieved_note}")
        
        # Supprimer la note
        print("\nSuppression de la note...")
        await client.delete_note(new_note.id)
        print("Note supprimée avec succès")
        
    finally:
        # Fermer le client
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 