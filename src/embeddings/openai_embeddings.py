from typing import List, Any
import openai
from src.config import get_settings

class OpenAIEmbeddings:
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def embed_query(self, text: str) -> List[float]:
        """Génère un embedding pour un texte donné."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings pour une liste de textes."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]

def get_embeddings(api_key: str = None, model: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """Factory function pour créer une instance d'OpenAIEmbeddings."""
    return OpenAIEmbeddings(api_key=api_key, model=model) 