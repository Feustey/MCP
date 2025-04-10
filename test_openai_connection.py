import os
from dotenv import load_dotenv
import openai
import asyncio
import json

# Chargement des variables d'environnement
load_dotenv()

async def test_openai_connection():
    """Fonction pour tester la connexion à OpenAI"""
    print(f"Test de connexion à l'API OpenAI...")
    
    # Utilisation directe de la nouvelle clé
    api_key = "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"
    print(f"Utilisation directe de la clé API: {api_key[:15]}...{api_key[-15:]}")
    
    # Configuration du client OpenAI avec la clé fournie directement
    client = openai.OpenAI(api_key=api_key)
    
    # Test des différents endpoints
    
    # 1. Test de création d'embedding
    try:
        print("\nTest de création d'embedding...")
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input="Ceci est un test de connexion à l'API OpenAI."
        )
        print(f"Embedding créé avec succès. Dimensions: {len(response.data[0].embedding)}")
        print(f"Premier embedding (5 premiers éléments): {response.data[0].embedding[:5]}")
    except Exception as e:
        print(f"Erreur lors de la création d'embedding: {str(e)}")
    
    # 2. Test de complétion (chat)
    try:
        print("\nTest de complétion chat...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Vous êtes un assistant utile."},
                {"role": "user", "content": "Bonjour, pouvez-vous me dire si la connexion fonctionne?"}
            ]
        )
        print(f"Complétion réussie!")
        print(f"Réponse: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Erreur lors de la complétion chat: {str(e)}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_openai_connection()) 