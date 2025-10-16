import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, AsyncIterator
from config.rag_config import settings as rag_settings
from src.clients.ollama_client import ollama_client, OllamaClientError

logger = logging.getLogger(__name__)


class OllamaRAGAdapter:
    """Adaptateur RAG pour utiliser Ollama pour embeddings et génération.
    
    Gère le formatage des prompts, la génération streaming/non-streaming,
    et le mapping des réponses vers le contrat RAG commun.
    """

    def __init__(
        self,
        embed_model: Optional[str] = None,
        gen_model: Optional[str] = None,
        dimension: int = 1536,
        num_ctx: int = 8192,
        fallback_model: str = "llama3:8b-instruct",
    ):
        self.dimension = dimension  # nomic-embed-text: 768, mais config peut forcer 1536
        self.embed_model = embed_model or rag_settings.EMBED_MODEL
        self.gen_model = gen_model or rag_settings.GEN_MODEL
        self.fallback_model = fallback_model
        self.num_ctx = num_ctx

    def get_embedding(self, text: str) -> List[float]:
        """Génère un embedding (version sync-compatible pour RAGWorkflow).
        
        Note: Cette méthode utilise asyncio.run() pour compatibilité avec le code existant.
        Pour une vraie implémentation async, utiliser get_embedding_async().
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si déjà dans une boucle async, créer une nouvelle boucle
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, ollama_client.embed(text, self.embed_model))
                    return future.result()
            else:
                return loop.run_until_complete(ollama_client.embed(text, self.embed_model))
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def get_embedding_async(self, text: str) -> List[float]:
        """Génère un embedding (version async native)."""
        return await ollama_client.embed(text, self.embed_model)

    async def get_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Génère des embeddings pour un batch de textes."""
        return await ollama_client.embed_batch(texts, self.embed_model)

    def _format_prompt(self, messages: List[Dict[str, Any]], lang: str = "fr") -> str:
        """Formate les messages en un prompt compatible Llama 3.
        
        Args:
            messages: Liste de messages avec role (system/user/assistant) et content
            lang: Langue cible (fr/en)
        
        Returns:
            Prompt formaté pour Ollama
        """
        system_parts = []
        user_parts = []
        
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            
            if role == "system":
                system_parts.append(content)
            elif role == "user":
                user_parts.append(content)
            elif role == "assistant":
                # Peut être ignoré ou intégré selon le contexte
                pass
        
        # Construction du prompt
        prompt_parts = []
        
        if system_parts:
            system_text = "\n\n".join(system_parts)
            prompt_parts.append(f"<|system|>\n{system_text}\n<|end|>")
        
        if user_parts:
            user_text = "\n\n".join(user_parts)
            prompt_parts.append(f"<|user|>\n{user_text}\n<|end|>")
        
        prompt_parts.append("<|assistant|>")
        
        return "\n".join(prompt_parts)

    def generate_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 600,
        lang: str = "fr",
    ) -> str:
        """Génère une complétion (version sync-compatible).
        
        Args:
            messages: Liste de messages avec role et content
            temperature: Température de génération (0.0-1.0)
            max_tokens: Nombre max de tokens à générer
            lang: Langue cible (fr/en)
        
        Returns:
            Texte généré, nettoyé
        """
        prompt = self._format_prompt(messages, lang)
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        ollama_client.generate(
                            prompt=prompt,
                            model=self.gen_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            num_ctx=self.num_ctx,
                        )
                    )
                    response = future.result()
            else:
                response = loop.run_until_complete(
                    ollama_client.generate(
                        prompt=prompt,
                        model=self.gen_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        num_ctx=self.num_ctx,
                    )
                )
            
            return self._clean_response(response)
        
        except OllamaClientError as e:
            logger.error(f"Generation failed with {self.gen_model}, trying fallback: {e}")
            try:
                # Fallback vers modèle 8B
                loop = asyncio.get_event_loop()
                response = loop.run_until_complete(
                    ollama_client.generate(
                        prompt=prompt,
                        model=self.fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        num_ctx=self.num_ctx,
                    )
                )
                return self._clean_response(response) + "\n\n[Note: réponse générée en mode dégradé]"
            except Exception as fallback_error:
                logger.error(f"Fallback generation also failed: {fallback_error}")
                raise

    async def generate_completion_async(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 600,
        lang: str = "fr",
    ) -> str:
        """Génère une complétion (version async native)."""
        prompt = self._format_prompt(messages, lang)
        
        try:
            response = await ollama_client.generate(
                prompt=prompt,
                model=self.gen_model,
                temperature=temperature,
                max_tokens=max_tokens,
                num_ctx=self.num_ctx,
            )
            return self._clean_response(response)
        
        except OllamaClientError as e:
            logger.warning(f"Generation failed with {self.gen_model}, trying fallback: {e}")
            response = await ollama_client.generate(
                prompt=prompt,
                model=self.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
                num_ctx=self.num_ctx,
            )
            return self._clean_response(response) + "\n\n[Note: réponse générée en mode dégradé]"

    async def generate_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 600,
        lang: str = "fr",
    ) -> AsyncIterator[str]:
        """Génère une complétion en streaming."""
        prompt = self._format_prompt(messages, lang)
        
        try:
            async for chunk in ollama_client.generate_stream(
                prompt=prompt,
                model=self.gen_model,
                temperature=temperature,
                max_tokens=max_tokens,
                num_ctx=self.num_ctx,
            ):
                yield chunk
        
        except OllamaClientError as e:
            logger.warning(f"Stream failed with {self.gen_model}, trying fallback: {e}")
            async for chunk in ollama_client.generate_stream(
                prompt=prompt,
                model=self.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
                num_ctx=self.num_ctx,
            ):
                yield chunk

    def _clean_response(self, response: str) -> str:
        """Nettoie la réponse générée.
        
        - Retire les balises de formatage Llama
        - Retire les espaces inutiles
        - Normalise les citations
        """
        # Retirer les balises Llama potentielles
        response = re.sub(r'<\|[^|]+\|>', '', response)
        
        # Normaliser les espaces
        response = re.sub(r'\s+', ' ', response)
        response = response.strip()
        
        return response

    def map_to_rag_response(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        confidence: Optional[float] = None,
        degraded: bool = False,
    ) -> Dict[str, Any]:
        """Mappe une réponse vers le contrat RAG standardisé.
        
        Args:
            answer: Texte de la réponse
            sources: Liste des sources (chunks) utilisées
            confidence: Score de confiance (optionnel)
            degraded: Flag indiquant si fallback utilisé
        
        Returns:
            Réponse formatée selon le contrat RAG
        """
        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "degraded": degraded,
            "model": self.fallback_model if degraded else self.gen_model,
            "embed_model": self.embed_model,
            "embed_version": rag_settings.EMBED_VERSION,
        }


