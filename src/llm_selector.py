import os
from typing import Optional, Dict, Any
import httpx
import json
import asyncio

def ask_llm_choice():
    try:
        choice = input("Souhaitez-vous utiliser OpenAI ou Ollama comme moteur LLM ? [openai/ollama] : ").strip().lower()
    except Exception:
        # fallback non interactif (ex: API)
        choice = os.getenv("LLM_PROVIDER", "openai").lower()
    if choice not in ["openai", "ollama"]:
        print("Choix invalide, utilisation de OpenAI par défaut.")
        choice = "openai"
    return choice

class OllamaLLM:
    def __init__(self, model: str = "llama3", **model_params):
        """
        Initialise le client Ollama.
        
        Args:
            model: Nom du modèle à utiliser (par défaut: llama3)
            **model_params: Paramètres additionnels pour le modèle
        """
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model
        self.model_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            **model_params  # Permet de surcharger les paramètres par défaut
        }
        self.max_retries = 3
        self.retry_delay = 1  # secondes

    async def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Génère une réponse à partir d'un prompt avec mécanisme de retry.
        
        Args:
            prompt: Le prompt à envoyer au modèle
            
        Returns:
            Dict: La réponse du modèle avec la clé 'text' contenant la génération
        """
        url = f"{self.base_url}/api/generate"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            **self.model_params
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    result = response.json()
                    
                    return {
                        "text": result.get("response", ""),
                        "model": self.model,
                        "success": True
                    }
            except Exception as e:
                print(f"Tentative {attempt+1}/{self.max_retries}: Erreur lors de la génération avec Ollama: {e}")
                if attempt == self.max_retries - 1:
                    return {
                        "text": "Je n'ai pas pu générer de réponse en raison d'une erreur technique.",
                        "model": self.model,
                        "success": False,
                        "error": str(e)
                    }
                await asyncio.sleep(self.retry_delay)
    
    async def acomplete(self, system_prompt: str, prompt: str) -> Dict[str, Any]:
        """
        Interface compatible avec d'autres LLMs utilisant le format completion.
        
        Args:
            system_prompt: Le prompt système
            prompt: Le prompt utilisateur
            
        Returns:
            Dict: La réponse du modèle
        """
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        result = await self.generate(full_prompt)
        return type('obj', (object,), {'text': result.get('text', '')})

    async def get_embedding(self, text: str, max_retries=3) -> list:
        """
        Obtient l'embedding d'un texte via Ollama.
        
        Args:
            text: Le texte à encoder
            max_retries: Nombre maximum de tentatives
            
        Returns:
            list: Le vecteur d'embedding
        """
        url = f"{self.base_url}/api/embeddings"
        
        data = {
            "model": self.model,
            "prompt": text
        }
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    result = response.json()
                    return result.get("embedding", [])
            except Exception as e:
                print(f"Tentative {attempt+1}/{max_retries}: Erreur lors de la génération de l'embedding: {e}")
                if attempt == max_retries - 1:
                    # Retourner un embedding vide plutôt que de lever une exception
                    import numpy as np
                    return np.zeros(384).tolist()  # Dimension par défaut
                await asyncio.sleep(self.retry_delay)

class OpenAILLM:
    def __init__(self, model: str = "gpt-3.5-turbo", **model_params):
        """
        Initialise le client OpenAI.
        
        Args:
            model: Nom du modèle à utiliser (par défaut: gpt-3.5-turbo)
            **model_params: Paramètres additionnels pour le modèle
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY non définie dans les variables d'environnement")
            
        self.model = model
        self.model_params = {
            "temperature": 0.7,
            "max_tokens": 500,
            **model_params  # Permet de surcharger les paramètres par défaut
        }
        self.max_retries = 3
        self.retry_delay = 1  # secondes

    async def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Génère une réponse à partir d'un prompt.
        
        Args:
            prompt: Le prompt à envoyer au modèle
            
        Returns:
            Dict: La réponse du modèle avec la clé 'text' contenant la génération
        """
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **self.model_params
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data, headers=headers)
                    response.raise_for_status()
                    result = response.json()
                    
                    return {
                        "text": result["choices"][0]["message"]["content"],
                        "model": self.model,
                        "success": True
                    }
            except Exception as e:
                print(f"Tentative {attempt+1}/{self.max_retries}: Erreur lors de la génération avec OpenAI: {e}")
                if attempt == self.max_retries - 1:
                    return {
                        "text": "Je n'ai pas pu générer de réponse en raison d'une erreur technique.",
                        "model": self.model,
                        "success": False,
                        "error": str(e)
                    }
                await asyncio.sleep(self.retry_delay)
    
    async def acomplete(self, system_prompt: str, prompt: str) -> Dict[str, Any]:
        """
        Interface compatible avec d'autres LLMs utilisant le format completion.
        
        Args:
            system_prompt: Le prompt système
            prompt: Le prompt utilisateur
            
        Returns:
            Dict: La réponse du modèle
        """
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
            **self.model_params
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data, headers=headers)
                    response.raise_for_status()
                    result = response.json()
                    
                    return type('obj', (object,), {'text': result["choices"][0]["message"]["content"]})
            except Exception as e:
                print(f"Tentative {attempt+1}/{self.max_retries}: Erreur lors de l'appel à OpenAI: {e}")
                if attempt == self.max_retries - 1:
                    return type('obj', (object,), {'text': "Je n'ai pas pu générer de réponse en raison d'une erreur technique."})
                await asyncio.sleep(self.retry_delay)

    async def get_embedding(self, text: str, max_retries=3) -> list:
        """
        Obtient l'embedding d'un texte via OpenAI.
        
        Args:
            text: Le texte à encoder
            max_retries: Nombre maximum de tentatives
            
        Returns:
            list: Le vecteur d'embedding
        """
        url = "https://api.openai.com/v1/embeddings"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "text-embedding-ada-002",  # Modèle d'embedding par défaut
            "input": text
        }
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=data, headers=headers)
                    response.raise_for_status()
                    result = response.json()
                    return result["data"][0]["embedding"]
            except Exception as e:
                print(f"Tentative {attempt+1}/{max_retries}: Erreur lors de la génération de l'embedding: {e}")
                if attempt == max_retries - 1:
                    # Retourner un embedding vide plutôt que de lever une exception
                    import numpy as np
                    return np.zeros(1536).tolist()  # Dimension pour les embeddings OpenAI
                await asyncio.sleep(self.retry_delay)

def get_llm(llm_type: str = "ollama", **kwargs) -> Any:
    """
    Retourne une instance du LLM spécifié.
    
    Args:
        llm_type: Type de LLM ("openai", "ollama", etc.)
        **kwargs: Arguments supplémentaires pour l'initialisation du LLM
        
    Returns:
        Une instance du LLM demandé
    """
    if llm_type.lower() == "ollama":
        return OllamaLLM(**kwargs)
    elif llm_type.lower() == "openai":
        return OpenAILLM(**kwargs)
    else:
        raise ValueError(f"Type de LLM non supporté: {llm_type}") 