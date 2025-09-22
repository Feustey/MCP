"""
Adaptateur pour utiliser Anthropic dans le système RAG
Utilise sentence-transformers pour les embeddings car Anthropic n'offre pas ce service
"""

import os
import logging
from typing import List, Dict, Any
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class AnthropicRAGAdapter:
    def __init__(self):
        # Client Anthropic pour la génération de texte
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Modèle d'embeddings local (alternative à OpenAI embeddings)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # Dimension pour all-MiniLM-L6-v2
        
    def get_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding pour le texte donné.
        Utilise sentence-transformers au lieu d'OpenAI.
        """
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'embedding: {str(e)}")
            raise
    
    def generate_completion(self, messages: List[Dict[str, str]], 
                          temperature: float = 0.7, 
                          max_tokens: int = 500) -> str:
        """
        Génère une réponse en utilisant Anthropic Claude.
        Adapte le format des messages d'OpenAI vers Anthropic.
        """
        try:
            # Extraction du system prompt et du message utilisateur
            system_prompt = ""
            user_message = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_message = msg["content"]
            
            # Appel à l'API Anthropic
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Modèle économique et rapide
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération avec Anthropic: {str(e)}")
            raise
    
    @property
    def dimension(self) -> int:
        """Retourne la dimension des embeddings."""
        return self.embedding_dimension