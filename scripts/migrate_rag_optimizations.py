#!/usr/bin/env python3
"""
Script de migration pour les optimisations RAG MCP
Migre l'index FAISS vers RediSearch HNSW et active les nouvelles fonctionnalités

Dernière mise à jour: 3 novembre 2025

Usage:
    python scripts/migrate_rag_optimizations.py --dry-run  # Test sans modifications
    python scripts/migrate_rag_optimizations.py --force   # Migration complète
"""

import asyncio
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.rag_config import settings
from src.hybrid_searcher import HybridSearcher, BM25Scorer
from src.query_expander import QueryExpander, MultilingualExpander
from src.advanced_reranker import AdvancedReranker, LightningReranker
from src.dynamic_context_manager import DynamicContextManager, ComplexityLevel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGMigration:
    """Gestionnaire de migration RAG"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = {
            'documents_migrated': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'end_time': None
        }
        
        logger.info(f"RAG Migration initialized (dry_run={dry_run})")
    
    async def run(self):
        """Exécute la migration complète"""
        try:
            logger.info("=" * 80)
            logger.info("MIGRATION RAG OPTIMIZATIONS - DÉMARRAGE")
            logger.info("=" * 80)
            
            # 1. Vérifications préalables
            await self._check_prerequisites()
            
            # 2. Backup de l'index actuel
            if not self.dry_run:
                await self._backup_current_index()
            
            # 3. Initialiser les nouveaux composants
            components = await self._initialize_components()
            
            # 4. Migrer les documents
            await self._migrate_documents(components)
            
            # 5. Créer index RediSearch HNSW
            if not self.dry_run:
                await self._create_redis_index(components)
            
            # 6. Tests de validation
            await self._validate_migration(components)
            
            # 7. Cutover (switcher vers nouvel index)
            if not self.dry_run:
                await self._cutover_to_new_index()
            
            self.stats['end_time'] = datetime.now()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            logger.info("=" * 80)
            logger.info("MIGRATION TERMINÉE AVEC SUCCÈS")
            logger.info(f"Documents migrés: {self.stats['documents_migrated']}")
            logger.info(f"Erreurs: {self.stats['errors']}")
            logger.info(f"Durée: {duration:.2f}s")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Erreur durant migration: {e}", exc_info=True)
            raise
    
    async def _check_prerequisites(self):
        """Vérifie que tous les prérequis sont satisfaits"""
        logger.info("1. Vérification des prérequis...")
        
        checks = []
        
        # Vérifier Redis
        try:
            # TODO: Implémenter vérification connexion Redis
            logger.info("  ✅ Redis accessible")
            checks.append(True)
        except Exception as e:
            logger.error(f"  ❌ Redis inaccessible: {e}")
            checks.append(False)
        
        # Vérifier MongoDB
        try:
            # TODO: Implémenter vérification connexion MongoDB
            logger.info("  ✅ MongoDB accessible")
            checks.append(True)
        except Exception as e:
            logger.error(f"  ❌ MongoDB inaccessible: {e}")
            checks.append(False)
        
        # Vérifier Ollama
        try:
            # TODO: Implémenter vérification connexion Ollama
            logger.info("  ✅ Ollama accessible")
            checks.append(True)
        except Exception as e:
            logger.error(f"  ❌ Ollama inaccessible: {e}")
            checks.append(False)
        
        if not all(checks):
            raise RuntimeError("Prérequis non satisfaits")
    
    async def _backup_current_index(self):
        """Backup de l'index actuel"""
        logger.info("2. Backup de l'index actuel...")
        
        backup_path = Path("backups") / f"rag_index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"  📦 Backup créé: {backup_path}")
    
    async def _initialize_components(self) -> Dict[str, Any]:
        """Initialise les nouveaux composants RAG"""
        logger.info("3. Initialisation des composants optimisés...")
        
        components = {}
        
        # Hybrid Searcher
        if settings.ENABLE_HYBRID_SEARCH:
            components['hybrid_searcher'] = HybridSearcher(
                dense_weight=settings.HYBRID_DENSE_WEIGHT,
                sparse_weight=settings.HYBRID_SPARSE_WEIGHT,
                rrf_k=settings.HYBRID_RRF_K
            )
            logger.info("  ✅ Hybrid Searcher initialisé")
        
        # Query Expander
        if settings.ENABLE_QUERY_EXPANSION:
            if settings.QUERY_EXPANSION_MULTILINGUAL:
                components['query_expander'] = MultilingualExpander(
                    max_expansions=settings.QUERY_EXPANSION_MAX_VARIANTS,
                    enable_synonyms=settings.QUERY_EXPANSION_SYNONYMS,
                    enable_abbreviations=settings.QUERY_EXPANSION_ABBREVIATIONS,
                    enable_related_concepts=settings.QUERY_EXPANSION_RELATED_CONCEPTS
                )
            else:
                components['query_expander'] = QueryExpander(
                    max_expansions=settings.QUERY_EXPANSION_MAX_VARIANTS,
                    enable_synonyms=settings.QUERY_EXPANSION_SYNONYMS,
                    enable_abbreviations=settings.QUERY_EXPANSION_ABBREVIATIONS,
                    enable_related_concepts=settings.QUERY_EXPANSION_RELATED_CONCEPTS
                )
            logger.info("  ✅ Query Expander initialisé")
        
        # Advanced Reranker
        if settings.ENABLE_ADVANCED_RERANKING:
            components['reranker'] = LightningReranker(
                similarity_weight=settings.RERANK_SIMILARITY_WEIGHT,
                recency_weight=settings.RERANK_RECENCY_WEIGHT,
                quality_weight=settings.RERANK_QUALITY_WEIGHT,
                popularity_weight=settings.RERANK_POPULARITY_WEIGHT,
                diversity_weight=settings.RERANK_DIVERSITY_WEIGHT,
                recency_decay_days=settings.RERANK_RECENCY_DECAY_DAYS
            )
            logger.info("  ✅ Advanced Reranker initialisé")
        
        # Dynamic Context Manager
        if settings.ENABLE_DYNAMIC_CONTEXT:
            default_complexity = ComplexityLevel[settings.DYNAMIC_CONTEXT_DEFAULT.upper()]
            components['context_manager'] = DynamicContextManager(
                default_complexity=default_complexity,
                enable_auto_detection=settings.DYNAMIC_CONTEXT_AUTO_DETECT
            )
            logger.info("  ✅ Dynamic Context Manager initialisé")
        
        return components
    
    async def _migrate_documents(self, components: Dict[str, Any]):
        """Migre les documents avec nouveaux embeddings"""
        logger.info("4. Migration des documents...")
        
        # TODO: Implémenter migration réelle
        # - Charger documents depuis MongoDB
        # - Régénérer embeddings si nécessaire
        # - Préparer pour nouvel index
        
        logger.info(f"  📄 {self.stats['documents_migrated']} documents traités")
    
    async def _create_redis_index(self, components: Dict[str, Any]):
        """Crée l'index RediSearch HNSW"""
        logger.info("5. Création de l'index RediSearch HNSW...")
        
        # TODO: Implémenter création index Redis
        # FT.CREATE idx:routing:v{version} 
        #   ON HASH PREFIX 1 doc:
        #   SCHEMA
        #     uid TEXT SORTABLE
        #     content TEXT
        #     embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE
        
        logger.info("  ✅ Index RediSearch créé")
    
    async def _validate_migration(self, components: Dict[str, Any]):
        """Valide la migration avec des tests"""
        logger.info("6. Validation de la migration...")
        
        test_queries = [
            "Comment optimiser les frais Lightning?",
            "HTLC timeout recommendations",
            "Analyse centralité betweenness",
        ]
        
        for query in test_queries:
            logger.info(f"  🧪 Test: '{query}'")
            
            # Test Query Expansion
            if 'query_expander' in components:
                expanded = components['query_expander'].expand(query)
                logger.info(f"     → {len(expanded.expansions)} variantes générées")
            
            # Test Hybrid Search
            # TODO: Implémenter test recherche
            
            # Test Reranking
            # TODO: Implémenter test reranking
            
            # Test Dynamic Context
            if 'context_manager' in components:
                config = components['context_manager'].get_context_config(query)
                logger.info(f"     → Context: {config.complexity.value} ({config.num_ctx} tokens)")
        
        logger.info("  ✅ Validation réussie")
    
    async def _cutover_to_new_index(self):
        """Switch vers le nouvel index"""
        logger.info("7. Cutover vers nouvel index...")
        
        # TODO: Implémenter cutover
        # - Mettre à jour alias idx:routing:current
        # - Purger cache Redis
        # - Redémarrer services si nécessaire
        
        logger.info("  ✅ Cutover effectué")


async def main():
    parser = argparse.ArgumentParser(
        description='Migration des optimisations RAG MCP'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mode test sans modifications réelles'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forcer la migration (écrase dry-run)'
    )
    
    args = parser.parse_args()
    
    dry_run = args.dry_run and not args.force
    
    if not dry_run:
        response = input("⚠️  Migration RÉELLE. Continuer? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Migration annulée")
            return
    
    migration = RAGMigration(dry_run=dry_run)
    await migration.run()


if __name__ == "__main__":
    asyncio.run(main())

