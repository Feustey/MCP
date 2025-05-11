import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from llama_index.core.llms import LLM
from src.llm_selector import get_llm, ask_llm_choice

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryExpander:
    """
    Classe qui utilise un LLM pour améliorer les requêtes utilisateurs en:
    1. Réécrivant la requête pour la rendre plus précise
    2. Générant des sous-requêtes complémentaires
    3. Identifiant des mots-clés importants
    """
    
    def __init__(self, llm=None):
        if llm is None:
            choice = ask_llm_choice()
            llm = get_llm(choice)
        self.llm = llm
        
    async def expand_query(self, query: str) -> Dict[str, Any]:
        """
        Étend la requête originale en utilisant un LLM pour générer:
        - Une requête réécrite plus efficace pour la recherche
        - Des sous-requêtes complémentaires pour élargir la recherche
        - Des mots-clés importants à rechercher
        
        Args:
            query: La requête utilisateur originale
            
        Returns:
            Dict contenant la requête réécrite, les sous-requêtes et les mots-clés
        """
        try:
            # Construire le prompt pour le LLM
            system_prompt = """Tu es un expert en reformulation de requêtes pour un système de recherche d'information.\nTa tâche est d'analyser une requête utilisateur et de la transformer pour optimiser les résultats de recherche.\nTu dois:\n1. Réécrire la requête pour la rendre plus précise et spécifique au domaine (ici: réseau Lightning Network et nœuds Bitcoin)\n2. Générer 2-3 sous-requêtes complémentaires qui couvrent différents aspects de la question initiale\n3. Extraire 3-5 mots-clés ou termes techniques importants de la requête\n\nFormats mal structurés à éviter:\n- \"Requête reformulée: ...\"\n- \"Sous-requêtes: 1. ... 2. ...\"\n\nRéponds UNIQUEMENT au format JSON suivant:\n{\n  \"rewritten_query\": \"la requête réécrite et améliorée\",\n  \"sub_queries\": [\"sous-requête 1\", \"sous-requête 2\", \"sous-requête 3\"],\n  \"keywords\": [\"mot-clé 1\", \"mot-clé 2\", \"mot-clé 3\", \"mot-clé 4\", \"mot-clé 5\"]\n}"""
            user_prompt = f"""Requête originale: {query}\n\nAnalyse-la et génère une version améliorée pour un système de recherche d'information spécialisé dans le réseau Lightning Network et les nœuds Bitcoin."""

            # Appeler le LLM pour obtenir les expansions
            logger.info(f"Expansion de la requête: {query}")
            if hasattr(self.llm, "chat"):
                # OpenAI
                response = await self.llm.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                response_text = response.choices[0].message.content
            else:
                # Ollama (ou autre LLM compatible llama_index)
                response = await self.llm.acomplete(
                    system_prompt=system_prompt,
                    prompt=user_prompt
                )
                response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Extraire et parser la réponse JSON
            try:
                # Trouver le JSON dans la réponse en supprimant le texte avant et après
                json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    expanded = json.loads(json_str)
                    
                    # Valider la structure de la réponse
                    if not all(k in expanded for k in ["rewritten_query", "sub_queries", "keywords"]):
                        logger.warning(f"Réponse mal structurée: {expanded}")
                        # Créer une structure par défaut
                        expanded = self._create_fallback_expansion(query, expanded)
                else:
                    logger.warning(f"Impossible de trouver du JSON dans la réponse: {response_text}")
                    expanded = self._create_fallback_expansion(query)
            except json.JSONDecodeError:
                logger.warning(f"Erreur de décodage JSON: {response_text}")
                expanded = self._create_fallback_expansion(query)
                
            logger.info(f"Requête étendue: {expanded['rewritten_query']}")
            logger.info(f"Sous-requêtes: {expanded['sub_queries']}")
            
            return expanded
        except Exception as e:
            logger.error(f"Erreur lors de l'expansion de la requête: {str(e)}")
            # En cas d'erreur, retourner une version minimale avec juste la requête originale
            return {
                "rewritten_query": query,
                "sub_queries": [],
                "keywords": []
            }
            
    def _create_fallback_expansion(self, query: str, partial_result: Dict = None) -> Dict[str, Any]:
        """Crée une expansion de secours en cas d'échec"""
        result = {"rewritten_query": query, "sub_queries": [], "keywords": []}
        
        # Intégrer toutes les informations valides de partial_result si disponible
        if partial_result and isinstance(partial_result, dict):
            if "rewritten_query" in partial_result and isinstance(partial_result["rewritten_query"], str):
                result["rewritten_query"] = partial_result["rewritten_query"]
            
            if "sub_queries" in partial_result and isinstance(partial_result["sub_queries"], list):
                result["sub_queries"] = [q for q in partial_result["sub_queries"] if isinstance(q, str)]
                
            if "keywords" in partial_result and isinstance(partial_result["keywords"], list):
                result["keywords"] = [k for k in partial_result["keywords"] if isinstance(k, str)]
                
        # Si toujours vide, essayer d'extraire des mots-clés basiques
        if not result["keywords"]:
            # Extraire les mots de plus de 3 caractères (potentiels mots-clés)
            words = [w for w in re.findall(r'\b\w+\b', query) if len(w) > 3]
            result["keywords"] = words[:5]  # Prendre maximum 5 mots
            
        return result

class QueryRouter:
    """
    Classe qui analyse une requête et détermine la meilleure stratégie de recherche
    en fonction de son contenu (ex: recherche exacte vs sémantique, filtrage spécifique, etc.)
    """
    
    def __init__(self):
        # Motifs de requêtes qui nécessitent différentes stratégies
        self.exact_patterns = [
            r'\b(pub[A-Za-z0-9]{8,})\b',  # Clés publiques
            r'\b([0-9a-fA-F]{64})\b',     # Hash Bitcoin (64 caractères hex)
            r'\"([^\"]+)\"',               # Texte entre guillemets (recherche exacte)
            r'\b(\d{6,})\b'                # Grands nombres (ex: montants)
        ]
        
        # Mots-clés indiquant un besoin de filtrage ou de tri spécifique
        self.filter_keywords = {
            'récent': {'field': 'timestamp', 'sort': 'desc'},
            'ancien': {'field': 'timestamp', 'sort': 'asc'},
            'score': {'field': 'score', 'sort': 'desc'},
            'capacité': {'field': 'capacity', 'sort': 'desc'},
            'frais': {'field': 'fee_rate', 'sort': 'asc'}
        }
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyse la requête et détermine la meilleure stratégie de recherche.
        
        Args:
            query: La requête utilisateur
            
        Returns:
            Dict contenant la stratégie et les paramètres de recherche recommandés
        """
        result = {
            'query': query,
            'exact_matches': [],
            'filters': [],
            'recommended_strategy': 'hybrid',  # Par défaut hybride
            'vector_weight': 0.7               # Poids par défaut pour la recherche vectorielle
        }
        
        # Rechercher des motifs exacts
        for pattern in self.exact_patterns:
            matches = re.findall(pattern, query)
            if matches:
                result['exact_matches'].extend(matches)
                # Si beaucoup de termes exacts, diminuer le poids vectoriel
                result['vector_weight'] = max(0.3, result['vector_weight'] - 0.1 * len(matches))
        
        # Vérifier les mots-clés pour filtrage ou tri
        query_lower = query.lower()
        for keyword, filter_info in self.filter_keywords.items():
            if keyword in query_lower:
                result['filters'].append({
                    'keyword': keyword,
                    'field': filter_info['field'],
                    'sort': filter_info['sort']
                })
        
        # Déterminer la stratégie recommandée
        if len(result['exact_matches']) > 0:
            # S'il y a des correspondances exactes importantes
            if re.search(r'\b([0-9a-fA-F]{64})\b', query):  # Hash complet - recherche très précise
                result['recommended_strategy'] = 'lexical'
                result['vector_weight'] = 0.1  # Presque entièrement lexical
            else:
                # Sinon, hybride mais penché vers lexical
                result['vector_weight'] = 0.4
        elif any(kw in query_lower for kw in ['définition', 'signifie', 'qu\'est-ce que']):
            # Questions de définition - privilégier la recherche sémantique
            result['vector_weight'] = 0.9
        
        # Déterminer si on doit utiliser des filtres spécifiques
        result['use_filters'] = len(result['filters']) > 0
        
        return result 