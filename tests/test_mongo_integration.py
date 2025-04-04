import pytest
import asyncio
from datetime import datetime
from src.models import Document, QueryHistory, SystemStats
from src.mongo_operations import MongoOperations
from src.rag import RAGWorkflow
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

@pytest.fixture
async def mongo_ops():
    """Fixture pour les opérations MongoDB"""
    ops = MongoOperations()
    await ops.db.documents.delete_many({})
    await ops.db.query_history.delete_many({})
    await ops.db.system_stats.delete_many({})
    yield ops

@pytest.fixture
async def rag_workflow():
    """Fixture pour le workflow RAG"""
    workflow = RAGWorkflow()
    await workflow._init_redis()
    yield workflow
    await workflow._close_redis()

@pytest.mark.asyncio
async def test_document_save_and_retrieve(mongo_ops):
    """Test la sauvegarde et la récupération d'un document"""
    # Création d'un document de test
    test_embedding = [0.1] * 1536  # Dimension des embeddings OpenAI
    doc = Document(
        content="Test document content",
        source="test.txt",
        embedding=test_embedding,
        metadata={"test": "value"}
    )
    
    # Sauvegarde du document
    doc_id = await mongo_ops.save_document(doc)
    assert doc_id is not None
    
    # Récupération du document
    retrieved_doc = await mongo_ops.get_document(doc_id)
    assert retrieved_doc is not None
    assert retrieved_doc.content == doc.content
    assert retrieved_doc.source == doc.source
    assert retrieved_doc.embedding == doc.embedding
    assert retrieved_doc.metadata == doc.metadata

@pytest.mark.asyncio
async def test_query_history(mongo_ops):
    """Test la sauvegarde et la récupération de l'historique des requêtes"""
    # Création d'une requête de test
    query_history = QueryHistory(
        query="Test query",
        response="Test response",
        context_docs=["doc1", "doc2"],
        processing_time=1.5,
        cache_hit=False,
        metadata={"test": "value"}
    )
    
    # Sauvegarde de la requête
    query_id = await mongo_ops.save_query_history(query_history)
    assert query_id is not None
    
    # Récupération des requêtes récentes
    recent_queries = await mongo_ops.get_recent_queries(limit=1)
    assert len(recent_queries) == 1
    assert recent_queries[0].query == query_history.query
    assert recent_queries[0].response == query_history.response

@pytest.mark.asyncio
async def test_system_stats(mongo_ops):
    """Test la gestion des statistiques du système"""
    # Création des statistiques de test
    stats = SystemStats(
        total_documents=10,
        total_queries=5,
        average_processing_time=1.5,
        cache_hit_rate=0.8
    )
    
    # Mise à jour des statistiques
    await mongo_ops.update_system_stats(stats)
    
    # Récupération des statistiques
    retrieved_stats = await mongo_ops.get_system_stats()
    assert retrieved_stats is not None
    assert retrieved_stats.total_documents == stats.total_documents
    assert retrieved_stats.total_queries == stats.total_queries
    assert retrieved_stats.average_processing_time == stats.average_processing_time
    assert retrieved_stats.cache_hit_rate == stats.cache_hit_rate

@pytest.mark.asyncio
async def test_documents_by_source(mongo_ops):
    """Test la récupération des documents par source"""
    # Création de plusieurs documents de test
    test_embedding = [0.1] * 1536
    docs = [
        Document(content=f"Test doc {i}", source="test.txt", embedding=test_embedding)
        for i in range(3)
    ]
    
    # Sauvegarde des documents
    for doc in docs:
        await mongo_ops.save_document(doc)
    
    # Récupération des documents par source
    retrieved_docs = await mongo_ops.get_documents_by_source("test.txt")
    assert len(retrieved_docs) == 3
    assert all(doc.source == "test.txt" for doc in retrieved_docs)

@pytest.mark.asyncio
async def test_rag_with_mongo_integration(rag_workflow, mongo_ops):
    """Test l'intégration complète du RAG avec MongoDB"""
    # Création d'un fichier de test
    test_dir = "test_data"
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, "test.txt")
    
    with open(test_file, "w") as f:
        f.write("Test content for RAG system. This is a test document.")
    
    # Ingestion du document
    await rag_workflow.ingest_documents(test_dir)
    
    # Vérification des statistiques
    stats = await mongo_ops.get_system_stats()
    assert stats is not None
    assert stats.total_documents > 0
    
    # Test d'une requête
    response = await rag_workflow.query("What is the test content?")
    assert response is not None
    
    # Vérification de l'historique des requêtes
    recent_queries = await mongo_ops.get_recent_queries(limit=1)
    assert len(recent_queries) == 1
    assert recent_queries[0].query == "What is the test content?"
    
    # Nettoyage
    os.remove(test_file)
    os.rmdir(test_dir) 