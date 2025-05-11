from src.rag import RAGWorkflow
from src.redis_operations import RedisOperations
import os
import logging
import asyncio
from fastapi import HTTPException

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis_ops = RedisOperations(redis_url=_redis_url)
_rag_workflow = None
_init_lock = asyncio.Lock()

async def get_rag_workflow():
    global _rag_workflow
    async with _init_lock:
        if _rag_workflow is None:
            try:
                _rag_workflow = RAGWorkflow(redis_ops=_redis_ops)
                await _rag_workflow.ensure_connected()
            except Exception as e:
                logging.error(f"[RAG] Erreur d'initialisation : {e}")
                raise HTTPException(status_code=500, detail=f"RAG init failed: {e}")
    return _rag_workflow

async def check_rag_health():
    health = {"redis": False, "mongo": False, "rag_instance": False}
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