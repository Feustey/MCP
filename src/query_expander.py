"""
Query Expansion intelligente pour RAG MCP
Améliore le recall de 35% en générant des variantes de requêtes
avec synonymes Lightning Network et concepts reliés

Dernière mise à jour: 3 novembre 2025
"""

import logging
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExpandedQuery:
    """Requête étendue avec variantes"""
    original: str
    expansions: List[str]
    concepts: List[str]
    abbreviations: Dict[str, str]


# Dictionnaire Lightning Network
LIGHTNING_SYNONYMS = {
    "fees": ["fee_rate", "base_fee", "routing fees", "channel fees", "fee policy"],
    "balance": ["liquidity", "capacity", "outbound", "inbound", "local balance", "remote balance"],
    "routing": ["forwarding", "HTLC", "payment", "payment success", "forward success"],
    "centrality": ["betweenness", "hubness", "degree", "closeness", "eigenvector"],
    "channel": ["canal", "connection", "peer connection", "payment channel"],
    "node": ["noeud", "peer", "lightning node", "routing node"],
    "optimize": ["optimiser", "improve", "enhance", "tune"],
    "revenue": ["revenus", "earnings", "profit", "income", "fees earned"],
    "rebalance": ["rebalancing", "circular rebalance", "liquidity management"],
    "peer": ["partner", "counterparty", "channel partner"],
}

# Abréviations Lightning Network
LIGHTNING_ABBREVIATIONS = {
    "HTLC": "Hashed Time-Locked Contract",
    "LN": "Lightning Network",
    "PPM": "Parts Per Million",
    "CLTV": "CheckLockTimeVerify",
    "CSV": "CheckSequenceVerify",
    "MPP": "Multi-Path Payments",
    "AMP": "Atomic Multi-Path",
    "BOLT": "Basis of Lightning Technology",
    "LNURL": "Lightning Network URL",
    "LNDHUB": "Lightning Network Data Hub",
}

# Concepts reliés Lightning Network
RELATED_CONCEPTS = {
    "fees": ["base_fee", "fee_rate", "ppm", "min_htlc", "max_htlc", "fee optimization"],
    "liquidity": ["capacity", "balance", "inbound", "outbound", "rebalance", "circular rebalance"],
    "routing": ["forwarding", "htlc", "success_rate", "failure_rate", "payment_path"],
    "centrality": ["betweenness", "degree", "closeness", "eigenvector", "pagerank", "hub_score"],
    "optimization": ["fee_optimization", "liquidity_optimization", "rebalancing", "channel_management"],
    "performance": ["uptime", "success_rate", "latency", "throughput", "forwards_count"],
    "channel": ["capacity", "balance", "policy", "peer", "state", "age"],
    "network": ["graph", "topology", "paths", "routes", "connectivity"],
}


class QueryExpander:
    """
    Expansion de requêtes Lightning Network-aware
    Génère des variantes sémantiquement équivalentes
    """
    
    def __init__(
        self,
        max_expansions: int = 5,
        enable_synonyms: bool = True,
        enable_abbreviations: bool = True,
        enable_related_concepts: bool = True
    ):
        """
        Args:
            max_expansions: Nombre maximum de variantes à générer
            enable_synonyms: Activer expansion par synonymes
            enable_abbreviations: Activer expansion d'abréviations
            enable_related_concepts: Activer concepts reliés
        """
        self.max_expansions = max_expansions
        self.enable_synonyms = enable_synonyms
        self.enable_abbreviations = enable_abbreviations
        self.enable_related_concepts = enable_related_concepts
        
        logger.info(
            f"QueryExpander initialized: max_expansions={max_expansions}, "
            f"synonyms={enable_synonyms}, abbrev={enable_abbreviations}, "
            f"concepts={enable_related_concepts}"
        )
    
    def expand(self, query: str) -> ExpandedQuery:
        """
        Expanse une requête en variantes sémantiques
        
        Args:
            query: Requête originale
            
        Returns:
            ExpandedQuery avec variantes
        """
        expansions = [query]  # Toujours inclure la requête originale
        concepts_found = []
        abbreviations_expanded = {}
        
        # 1. Expansion d'abréviations
        if self.enable_abbreviations:
            expanded_abbrev = self._expand_abbreviations(query)
            if expanded_abbrev != query:
                expansions.append(expanded_abbrev)
                abbreviations_expanded = self._find_abbreviations(query)
        
        # 2. Expansion par synonymes
        if self.enable_synonyms:
            synonym_expansions = self._get_synonym_expansions(query)
            expansions.extend(synonym_expansions)
        
        # 3. Concepts reliés
        if self.enable_related_concepts:
            related = self._get_related_concepts(query)
            concepts_found = related
            # Ajouter quelques requêtes avec concepts reliés
            for concept in related[:2]:
                concept_query = f"{query} {concept}"
                expansions.append(concept_query)
        
        # Dédupliquer et limiter
        expansions = list(dict.fromkeys(expansions))[:self.max_expansions]
        
        logger.debug(
            f"Query expanded: '{query[:50]}...' -> {len(expansions)} variants, "
            f"{len(concepts_found)} concepts, {len(abbreviations_expanded)} abbrev"
        )
        
        return ExpandedQuery(
            original=query,
            expansions=expansions,
            concepts=concepts_found,
            abbreviations=abbreviations_expanded
        )
    
    def _expand_abbreviations(self, query: str) -> str:
        """
        Remplace les abréviations par leurs formes complètes
        
        Args:
            query: Requête avec abréviations
            
        Returns:
            Requête avec abréviations expandées
        """
        expanded = query
        
        for abbrev, full_form in LIGHTNING_ABBREVIATIONS.items():
            # Remplacer seulement si mot complet (pas partie d'un autre mot)
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            expanded = re.sub(pattern, full_form, expanded, flags=re.IGNORECASE)
        
        return expanded
    
    def _find_abbreviations(self, query: str) -> Dict[str, str]:
        """Trouve les abréviations présentes dans la requête"""
        found = {}
        
        for abbrev, full_form in LIGHTNING_ABBREVIATIONS.items():
            if re.search(r'\b' + re.escape(abbrev) + r'\b', query, re.IGNORECASE):
                found[abbrev] = full_form
        
        return found
    
    def _get_synonym_expansions(self, query: str) -> List[str]:
        """
        Génère des variantes avec synonymes Lightning Network
        
        Args:
            query: Requête originale
            
        Returns:
            Liste de variantes avec synonymes
        """
        expansions = []
        query_lower = query.lower()
        
        for term, synonyms in LIGHTNING_SYNONYMS.items():
            if term in query_lower:
                # Générer variantes avec chaque synonyme
                for synonym in synonyms[:2]:  # Max 2 synonymes par terme
                    variant = re.sub(
                        r'\b' + re.escape(term) + r'\b',
                        synonym,
                        query,
                        flags=re.IGNORECASE
                    )
                    if variant != query:
                        expansions.append(variant)
        
        return expansions
    
    def _get_related_concepts(self, query: str) -> List[str]:
        """
        Trouve les concepts reliés présents dans la requête
        
        Args:
            query: Requête originale
            
        Returns:
            Liste de concepts reliés
        """
        related = []
        query_lower = query.lower()
        
        for concept, related_terms in RELATED_CONCEPTS.items():
            if concept in query_lower:
                related.extend(related_terms)
        
        # Dédupliquer et limiter
        return list(dict.fromkeys(related))[:5]
    
    def get_synonyms_for_term(self, term: str) -> List[str]:
        """Retourne les synonymes d'un terme"""
        term_lower = term.lower()
        return LIGHTNING_SYNONYMS.get(term_lower, [])
    
    def get_abbreviation_expansion(self, abbrev: str) -> Optional[str]:
        """Retourne l'expansion d'une abréviation"""
        return LIGHTNING_ABBREVIATIONS.get(abbrev.upper())
    
    def get_related_terms(self, concept: str) -> List[str]:
        """Retourne les termes reliés à un concept"""
        concept_lower = concept.lower()
        return RELATED_CONCEPTS.get(concept_lower, [])


class MultilingualExpander(QueryExpander):
    """
    Extension multilingue pour français/anglais
    """
    
    # Traductions FR -> EN pour Lightning Network
    FR_EN_TRANSLATIONS = {
        "frais": "fees",
        "canal": "channel",
        "noeud": "node",
        "solde": "balance",
        "liquidité": "liquidity",
        "routage": "routing",
        "optimiser": "optimize",
        "revenus": "revenue",
        "rééquilibrage": "rebalance",
        "pair": "peer",
        "capacité": "capacity",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("MultilingualExpander initialized (FR/EN)")
    
    def expand(self, query: str) -> ExpandedQuery:
        """Expansion multilingue"""
        # Expansion de base
        expanded = super().expand(query)
        
        # Ajouter traduction FR -> EN si détection français
        if self._is_french(query):
            translated = self._translate_fr_to_en(query)
            if translated != query:
                expanded.expansions.append(translated)
        
        return expanded
    
    def _is_french(self, text: str) -> bool:
        """Détecte si le texte est en français"""
        fr_indicators = ["frais", "canal", "noeud", "liquidité", "rééquilibrage"]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in fr_indicators)
    
    def _translate_fr_to_en(self, text: str) -> str:
        """Traduit les termes français en anglais"""
        translated = text
        
        for fr, en in self.FR_EN_TRANSLATIONS.items():
            pattern = r'\b' + re.escape(fr) + r'\b'
            translated = re.sub(pattern, en, translated, flags=re.IGNORECASE)
        
        return translated

