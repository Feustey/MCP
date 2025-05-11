import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from llama_index.core.schema import NodeWithScore, Node
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.llms import LLM
from src.llm_selector import get_llm, ask_llm_choice

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedResponseGenerator:
    """
    Générateur de réponses avancé avec prompt engineering sophistiqué
    et gestion optimisée de la fenêtre de contexte.
    """
    
    def __init__(self, llm=None, tokenizer=None):
        if llm is None:
            choice = ask_llm_choice()
            llm = get_llm(choice)
        self.llm = llm
        self.tokenizer = tokenizer
        self.max_tokens = 8000  # Taille max de la fenêtre de contexte
        self.debug_mode = False  # Mode debug pour afficher plus d'informations
        
    def _count_tokens(self, text: str) -> int:
        """Compte le nombre de tokens dans un texte."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Estimation approximative si pas de tokenizer
            return len(text.split())
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Tronque le texte pour qu'il tienne dans la limite de tokens."""
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            if len(tokens) <= max_tokens:
                return text
            
            # Tronquer et ajouter une indication
            truncated_tokens = tokens[:max_tokens-10]  # Espace pour "[tronqué]"
            truncated_text = self.tokenizer.decode(truncated_tokens)
            return truncated_text + " [tronqué]"
        else:
            # Estimation approximative
            words = text.split()
            if len(words) <= max_tokens:
                return text
            return " ".join(words[:max_tokens-1]) + " [tronqué]"
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Formate les métadonnées pour inclusion dans le prompt."""
        formatted = []
        
        if "source" in metadata:
            formatted.append(f"Source: {metadata['source']}")
        
        if "file_name" in metadata:
            formatted.append(f"Document: {metadata['file_name']}")
            
        if "update_date" in metadata or "created_at" in metadata:
            date = metadata.get("update_date", metadata.get("created_at", "Date inconnue"))
            formatted.append(f"Date: {date}")
            
        if "node_id" in metadata:
            formatted.append(f"ID Nœud: {metadata['node_id']}")
            
        if "alias" in metadata:
            formatted.append(f"Alias: {metadata['alias']}")
            
        if "document_type" in metadata:
            formatted.append(f"Type: {metadata['document_type']}")
            
        return " | ".join(formatted)
    
    def optimize_context_window(self, docs: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Optimise les documents pour qu'ils tiennent dans la fenêtre de contexte.
        
        Args:
            docs: Liste de documents avec contenu et scores
            query: Requête utilisateur pour calculer la similarité
            
        Returns:
            Liste optimisée de documents
        """
        # Estimer les tokens du prompt de base et de la requête
        base_tokens = 800  # Estimation pour les prompts système et utilisateur
        query_tokens = self._count_tokens(query)
        
        # Calculer les tokens disponibles pour les documents
        available_tokens = self.max_tokens - base_tokens - query_tokens
        
        # Trier les documents par score de pertinence
        sorted_docs = sorted(docs, key=lambda x: x.get('score', 0), reverse=True)
        
        final_docs = []
        total_tokens = 0
        
        # Stratégie 1: D'abord inclure les documents très pertinents (score > 0.7)
        high_relevance_docs = [d for d in sorted_docs if d.get('score', 0) > 0.7]
        for doc in high_relevance_docs:
            doc_tokens = self._count_tokens(doc['content'])
            
            # Si le document est trop grand, le tronquer
            if total_tokens + doc_tokens > available_tokens:
                space_left = available_tokens - total_tokens
                if space_left > 200:  # Au moins 200 tokens disponibles
                    truncated_content = self._truncate_text(doc['content'], space_left)
                    doc['content'] = truncated_content
                    doc['truncated'] = True
                    doc_tokens = self._count_tokens(truncated_content)
                    
                    if total_tokens + doc_tokens <= available_tokens:
                        final_docs.append(doc)
                        total_tokens += doc_tokens
            else:
                final_docs.append(doc)
                total_tokens += doc_tokens
        
        # Stratégie 2: Ajouter les documents de pertinence moyenne
        medium_relevance_docs = [d for d in sorted_docs if d.get('score', 0) <= 0.7 and d.get('score', 0) > 0.4 
                                and d not in high_relevance_docs]
        for doc in medium_relevance_docs:
            doc_tokens = self._count_tokens(doc['content'])
            
            if total_tokens + doc_tokens <= available_tokens:
                final_docs.append(doc)
                total_tokens += doc_tokens
            # Pour les docs moyennement pertinents, ne pas tronquer
        
        # Stratégie 3: Ajouter des documents de faible pertinence s'il reste de la place
        low_relevance_docs = [d for d in sorted_docs if d.get('score', 0) <= 0.4 
                             and d not in high_relevance_docs and d not in medium_relevance_docs]
        for doc in low_relevance_docs:
            doc_tokens = self._count_tokens(doc['content'])
            
            if total_tokens + doc_tokens <= available_tokens:
                final_docs.append(doc)
                total_tokens += doc_tokens
            # Pour les docs peu pertinents, ne pas tronquer
        
        # Réorganiser les docs par pertinence pour avoir les plus pertinents en premier
        final_docs = sorted(final_docs, key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Optimisation de la fenêtre de contexte: {len(sorted_docs)} docs -> {len(final_docs)} docs")
        logger.info(f"Utilisation de tokens: {total_tokens}/{available_tokens} ({(total_tokens/available_tokens)*100:.1f}%)")
        
        return final_docs
    
    def build_enhanced_prompt(self, query: str, docs: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Construit un prompt avancé avec formatage des sources et instructions structurées.
        
        Args:
            query: Requête utilisateur
            docs: Documents avec contenu et métadonnées
            
        Returns:
            Tuple contenant (system_prompt, user_prompt)
        """
        system_prompt = """Tu es un expert du réseau Lightning Network et de l'analyse de nœuds Bitcoin. 
Ta tâche est de fournir des analyses précises et des recommandations pertinentes 
basées uniquement sur le contexte fourni.

DIRECTIVES IMPORTANTES:
1. Utilise EXCLUSIVEMENT les informations du contexte fourni - n'invente rien.
2. Si tu ne trouves pas l'information dans le contexte, indique-le clairement.
3. Cite tes sources en référençant les numéros des documents.
4. Structure ta réponse de manière claire et organisée.
5. Pour les données techniques et statistiques, présente-les de façon précise et quantifiée.
6. Adapte ton niveau de détail à la complexité de la requête.
7. Utilise des listes à puces pour les points importants.
8. Inclus des exemples concrets quand c'est pertinent.
9. Privilégie la concision et la clarté.
10. Utilise un ton professionnel et technique."""

        # Formatage du contexte avec métadonnées
        formatted_context = []
        for i, doc in enumerate(docs):
            metadata = doc.get('metadata', {})
            meta_str = self._format_metadata(metadata)
            
            if doc.get('truncated', False):
                truncation_note = " [DOCUMENT TRONQUÉ]"
            else:
                truncation_note = ""
                
            formatted_context.append(f"[Document {i+1}{truncation_note} | {meta_str}]\n{doc['content']}\n")
        
        # Structurer le prompt utilisateur
        user_prompt = f"""Requête: {query}

Contexte:
{"".join(formatted_context)}

Réponds en utilisant EXCLUSIVEMENT les informations du contexte ci-dessus.
Structure ta réponse avec:
1. Résumé exécutif (synthèse des points clés)
2. Analyse détaillée avec données précises
3. Recommandations pratiques (si pertinent pour la requête)

Utilise des listes à puces ou numérotées pour les données importantes.
Cite tes sources en référençant les documents (ex: [Doc 1], [Doc 3]).
"""
        
        return system_prompt, user_prompt
    
    async def generate_response(self, query: str, nodes: List[NodeWithScore], keywords: List[str] = None) -> str:
        """
        Génère une réponse optimisée basée sur le query et les nodes retournés.
        
        Args:
            query: Requête utilisateur
            nodes: Nodes avec scores de pertinence
            keywords: Mots-clés importants (optionnel)
            
        Returns:
            Réponse générée
        """
        try:
            # Convertir les nodes en format plus facile à manipuler
            docs = []
            for node_with_score in nodes:
                doc = {
                    'content': node_with_score.node.text,
                    'score': node_with_score.score if node_with_score.score is not None else 0.0,
                    'metadata': node_with_score.node.metadata
                }
                docs.append(doc)
            
            # Optimiser les documents pour la fenêtre de contexte
            optimized_docs = self.optimize_context_window(docs, query)
            
            # Construire le prompt avancé
            system_prompt, user_prompt = self.build_enhanced_prompt(query, optimized_docs)
            
            # Ajouter les mots-clés au prompt système
            if keywords and len(keywords) > 0:
                system_prompt += f"\n\nMots-clés importants: {', '.join(keywords)}"
            
            # Génération de la réponse avec le LLM sélectionné
            if hasattr(self.llm, "chat"):
                # OpenAI
                response = await self.llm.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                response_text = response.choices[0].message.content
            else:
                # Ollama (ou autre LLM compatible llama_index)
                response = await self.llm.acomplete(
                    system_prompt=system_prompt,
                    prompt=user_prompt
                )
                response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Alternativement, utiliser CompactAndRefine si les optimisations manuelles
            # ne sont pas efficaces
            if not response_text or len(response_text.strip()) < 50:
                logger.warning("Réponse trop courte, utilisation de CompactAndRefine comme fallback")
                
                # Convertir les documents optimisés en nodes
                fallback_nodes = []
                for doc in optimized_docs:
                    node = Node(text=doc['content'], metadata=doc.get('metadata', {}))
                    fallback_nodes.append(NodeWithScore(node=node, score=doc.get('score', 0.0)))
                
                summarizer = CompactAndRefine(
                    llm=self.llm,
                    streaming=False,
                    system_prompt=system_prompt
                )
                
                try:
                    # Utiliser generate au lieu de asynthesize qui peut causer l'erreur ChatResponseAsyncGen
                    response = await summarizer.aget_response(
                        query=query,
                        nodes=fallback_nodes
                    )
                except AttributeError:
                    # Fallback si aget_response n'est pas disponible
                    response = CompactAndRefine(
                        llm=self.llm,
                        streaming=False,
                        system_prompt=system_prompt
                    ).get_response(
                        query=query,
                        nodes=fallback_nodes
                    )
                
                response_text = str(response)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse avancée: {str(e)}")
            # Utiliser CompactAndRefine comme fallback en cas d'erreur
            summarizer = CompactAndRefine(
                llm=self.llm,
                streaming=False
            )
            
            try:
                # Utiliser generate au lieu de asynthesize
                response = await summarizer.aget_response(
                    query=query,
                    nodes=nodes
                )
            except AttributeError:
                # Fallback si aget_response n'est pas disponible
                response = CompactAndRefine(
                    llm=self.llm,
                    streaming=False
                ).get_response(
                    query=query,
                    nodes=nodes
                )
            
            return str(response) 