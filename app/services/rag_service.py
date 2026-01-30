"""
RAG Service with graceful fallback when dependencies are missing
"""
import os
import logging
import asyncio
from fastapi import HTTPException

# Try to import RAG dependencies
try:
    from src.rag import RAGWorkflow
    from src.redis_operations import RedisOperations
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    logging.warning(f"[RAG] Module not available: {e}. RAG features disabled.")
    RAGWorkflow = None
    RedisOperations = None

_rag_workflow = None
_init_lock = asyncio.Lock()
_redis_ops = None

if RAG_AVAILABLE:
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis_ops = RedisOperations(redis_url=_redis_url)

async def get_rag_workflow():
    """Get RAG workflow instance or raise error if not available"""
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="RAG service is not available. Missing dependencies (sentence_transformers)."
        )
    
    global _rag_workflow
    async with _init_lock:
        if _rag_workflow is None:
            try:
                _rag_workflow = RAGWorkflow(redis_ops=_redis_ops)
                await _rag_workflow.ensure_connected()
            except Exception as e:
                err_msg = str(e).split("\n")[0][:100]
                logging.warning("[RAG] Init failed (MongoDB/Redis): %s", err_msg)
                raise HTTPException(status_code=500, detail=f"RAG init failed: {err_msg}")
    return _rag_workflow

async def check_rag_health():
    """Check RAG service health"""
    health = {
        "redis": False, 
        "mongo": False, 
        "rag_instance": False,
        "rag_available": RAG_AVAILABLE
    }
    
    if not RAG_AVAILABLE:
        return health
        
    try:
        await _redis_ops._init_redis()
        pong = await _redis_ops.redis.ping()
        health["redis"] = pong is True
    except Exception as e:
        logging.error(f"[RAG] Redis KO : {e}")
    try:
        rag = await get_rag_workflow()
        await rag.mongo_ops.ensure_connected()
        health["mongo"] = True
        health["rag_instance"] = True
    except Exception as e:
        logging.error(f"[RAG] Mongo ou instance KO : {e}")
    return health 