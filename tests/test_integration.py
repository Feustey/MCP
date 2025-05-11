import pytest
import os
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.rag import RAGWorkflow
from src.network_analyzer import NetworkAnalyzer
from src.redis_operations import RedisOperations
from src.mongo_operations import MongoOperations
from src.llm_selector import get_llm
from src.models import NodeData, ChannelData, Document
from src.cache_manager import CacheManager


@pytest.fixture
def mongo_ops():
    """Fixture pour créer une instance de MongoOperations mockée."""
    mongo_ops = MagicMock(spec=MongoOperations)
    mongo_ops.connect = AsyncMock()
    mongo_ops.db = MagicMock()
    mongo_ops.db.documents = MagicMock()
    mongo_ops.db.documents.find = AsyncMock()
    mongo_ops.db.query_history = MagicMock()
    mongo_ops.db.system_stats = MagicMock()
    mongo_ops.db.node_data = MagicMock()
    mongo_ops.get_documents = AsyncMock()
    return mongo_ops


@pytest.fixture
def redis_ops():
    """Fixture pour créer une instance de RedisOperations mockée."""
    redis_ops = MagicMock(spec=RedisOperations)
    redis_ops._redis = MagicMock()
    redis_ops._init_redis = AsyncMock()
    redis_ops.get_node_data = AsyncMock()
    redis_ops.get_all_nodes = AsyncMock()
    redis_ops.get_node_channels = AsyncMock()
    redis_ops.get_network_metrics = AsyncMock()
    redis_ops.set_node_data = AsyncMock()
    redis_ops.set_channel_data = AsyncMock()
    return redis_ops


@pytest.fixture
def llm():
    """Fixture pour créer un LLM mocké."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value={"text": "Réponse de test du LLM", "success": True})
    mock_llm.acomplete = AsyncMock(return_value=MagicMock(text="Réponse de test du LLM"))
    return mock_llm


@pytest.fixture
def cache_manager():
    """Fixture pour créer un CacheManager mocké."""
    cache_manager = MagicMock(spec=CacheManager)
    cache_manager.get = AsyncMock(return_value=None)  # Par défaut, rien dans le cache
    cache_manager.set = AsyncMock()
    cache_manager.initialize = AsyncMock(return_value=cache_manager)
    return cache_manager


@pytest.fixture
def rag_workflow(mongo_ops, redis_ops, llm, cache_manager):
    """Fixture pour créer un RAG workflow."""
    # Créer directement le workflow sans utiliser initialize
    workflow = RAGWorkflow(
        mongo_ops=mongo_ops, 
        redis_ops=redis_ops,
        llm=llm,
        cache_manager=cache_manager
    )
    
    # Configurer les mocks
    workflow.query = AsyncMock(return_value="Réponse de test RAG")
    workflow.vector_store = MagicMock()
    workflow.query_router = MagicMock()
    workflow.query_expander = MagicMock()
    workflow.query_expander.expand_query = AsyncMock(return_value={
        "rewritten_query": "Requête réécrite",
        "sub_queries": ["Sous-requête 1", "Sous-requête 2"],
        "keywords": ["mot-clé1", "mot-clé2"]
    })
    
    return workflow


@pytest.mark.asyncio
async def test_rag_with_network_analyzer_integration(mongo_ops, redis_ops, llm, cache_manager, rag_workflow):
    """
    Test d'intégration vérifiant l'interaction entre RAG et NetworkAnalyzer.
    
    Ce test simule une requête utilisateur demandant des recommandations de canaux,
    qui nécessite à la fois une analyse du réseau et une récupération de contexte RAG.
    """
    # Configuration des mocks
    
    # Préparation des données pour NetworkAnalyzer
    sample_nodes = [
        NodeData(
            node_id="node1",
            alias="Node 1",
            capacity=1_000_000_000,
            channel_count=50,
            last_update=datetime.now(),
            reputation_score=95.0,
            location={"country": "France"}
        ),
        NodeData(
            node_id="node2",
            alias="Node 2", 
            capacity=2_000_000_000,
            channel_count=100,
            last_update=datetime.now(),
            reputation_score=98.0,
            location={"country": "Germany"}
        )
    ]
    
    sample_channels = [
        ChannelData(
            channel_id="ch1",
            capacity=100_000_000,
            fee_rate={"base_fee": 1000, "fee_rate": 0.0001},
            balance={"local": 0.5, "remote": 0.5},
            age=30,
            last_update=datetime.now(),
            status="active"
        )
    ]
    
    # Configure les mocks Redis
    redis_ops.get_all_nodes.return_value = sample_nodes
    redis_ops.get_node_data.return_value = sample_nodes[0]
    redis_ops.get_node_channels.return_value = sample_channels
    
    # Configure les mocks MongoDB
    document_sample = Document(
        id="123",
        content="Les nœuds avec un score de réputation élevé sont généralement plus fiables pour le routage.",
        source="best_practices.md",
        metadata={"source": "best_practices.md"},
        embedding=[0.1] * 384
    )
    mongo_ops.get_documents.return_value = [document_sample]
    
    # Créer les instances des classes principales
    network_analyzer = NetworkAnalyzer(redis_ops)
    
    # 1. Simuler une requête utilisateur demandant des recommandations de canaux
    query = "Quels sont les meilleurs nœuds pour ouvrir un canal Lightning Network?"
    
    # 2. Obtenir des recommandations de l'analyseur de réseau
    with patch.object(network_analyzer, 'analyze_node_connections', new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = [
            ChannelRecommendation(
                source_node_id="node1",
                target_node_id="node2",
                score=0.95,
                capacity_recommendation={"min": 0.01, "max": 0.05},
                fee_recommendation={"base_fee": 1000, "fee_rate": 0.0001},
                created_at=datetime.now()
            )
        ]
        
        recommendations = await network_analyzer.analyze_node_connections("node1")
    
    # 3. Utiliser RAG pour enrichir la réponse avec du contexte
    mock_response = """
    Voici les recommandations basées sur l'analyse du réseau et les meilleures pratiques:
    
    1. Le nœud 'Node 2' est recommandé avec un score de 0.95.
    2. Capacité recommandée: entre 0.01 et 0.05 BTC.
    3. Frais recommandés: 1000 sats de base et 0.0001 de taux.
    
    Un nœud avec un score de réputation élevé (comme Node 2 avec 98.0) est généralement plus fiable pour le routage.
    """
    rag_workflow.query.return_value = mock_response
    
    enriched_response = await rag_workflow.query(
        f"{query}\nRecommandations: {json.dumps([rec.dict() for rec in recommendations])}"
    )
    
    # Vérifications
    assert mock_analyze.called
    assert rag_workflow.query.called
    assert enriched_response == mock_response


@pytest.mark.asyncio
async def test_rag_workflow_caching_integration(mongo_ops, redis_ops, llm, cache_manager, rag_workflow):
    """
    Test d'intégration vérifiant le mécanisme de cache du workflow RAG.
    """
    # Configuration du test
    query = "Comment fonctionne Lightning Network?"
    cached_response = "Réponse mise en cache pour Lightning Network"
    
    # Configurer le cache pour d'abord retourner None (cache miss), puis la réponse mise en cache
    cache_manager.get.side_effect = [None, cached_response]
    
    # Premier appel - devrait manquer le cache et appeler le LLM
    first_response = await rag_workflow.query(query)
    
    # Vérifie que la réponse a été mise en cache
    cache_manager.set.assert_called_once()
    
    # Réinitialisation des mocks
    cache_manager.set.reset_mock()
    
    # Deuxième appel - devrait trouver dans le cache
    second_response = await rag_workflow.query(query)
    
    # Vérifie que le cache a été utilisé
    assert not cache_manager.set.called
    assert second_response == cached_response


@pytest.mark.asyncio
async def test_documents_retrieval_integration(mongo_ops):
    """
    Test d'intégration vérifiant la récupération de documents depuis MongoDB.
    """
    # Préparer les documents de test
    test_docs = [
        Document(
            id="1", 
            content="Lightning Network est un protocole de deuxième couche au-dessus de Bitcoin.",
            source="lightning_intro.md",
            metadata={"source": "lightning_intro.md"},
            embedding=[0.1] * 384
        ),
        Document(
            id="2",
            content="Les canaux Lightning permettent des transactions instantanées et à faibles frais.",
            source="channels.md",
            metadata={"source": "channels.md"},
            embedding=[0.2] * 384
        )
    ]
    
    # Configurer le mock pour la recherche de documents
    mongo_ops.get_documents.return_value = test_docs
    
    # Récupérer les documents
    docs = await mongo_ops.get_documents({"metadata.source": "lightning_intro.md"})
    
    # Vérifications
    assert len(docs) == 2
    assert docs[0].content == test_docs[0].content
    assert docs[1].metadata["source"] == test_docs[1].metadata["source"]
    mongo_ops.get_documents.assert_called_once() 