from src.models import Document, QueryHistory, SystemStats
from src.mongo_operations import MongoOperations

# Import conditionnel de RAG
try:
    from src.rag import RAGWorkflow
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ RAG non disponible: {e}")
    RAGWorkflow = None
    RAG_AVAILABLE = False

from src.database import get_database
from src.network_analyzer import NetworkAnalyzer
from src.network_optimizer import NetworkOptimizer
from src.automation_manager import AutomationManager
from src.redis_operations import RedisOperations
from src.data_aggregator import DataAggregator

__all__ = [
    'Document', 
    'QueryHistory', 
    'SystemStats', 
    'MongoOperations', 
    'RAGWorkflow', 
    'RAG_AVAILABLE',
    'get_database',
    'NetworkAnalyzer',
    'NetworkOptimizer',
    'AutomationManager',
    'RedisOperations',
    'DataAggregator'
] 