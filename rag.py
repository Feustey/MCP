import nest_asyncio
import os
import hashlib
import json
from datetime import datetime, timedelta
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.settings import Settings
from llama_index.core.workflow import Event, Context, Workflow, StartEvent, StopEvent, step
from llama_index.core.schema import NodeWithScore
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.redis import RedisVectorStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.text_splitter import TokenTextSplitter
import redis.asyncio as redis
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class RetrieverEvent(Event):
    """Result of running retrieval"""
    nodes: list[NodeWithScore]

class RAGWorkflow(Workflow):
    def __init__(self, model_name="llama3.2", embedding_model="BAAI/bge-small-en-v1.5"):
        super().__init__()
        # Initialize LLM based on environment
        if os.environ.get("ENVIRONMENT") == "production":
            self.llm = OpenAI(model="gpt-3.5-turbo")
        else:
            self.llm = Ollama(model=model_name)
            
        self.embed_model = HuggingFaceEmbedding(model_name=embedding_model)
        
        # Configure global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        
        self.index = None
        self.redis_client = None
        self.vector_store = None
        
        # Redis configuration
        self.response_cache_ttl = int(os.getenv("RESPONSE_CACHE_TTL", "3600"))  # 1 hour default
        self.redis_max_memory = os.getenv("REDIS_MAX_MEMORY", "2gb")
        self.redis_max_memory_policy = os.getenv("REDIS_MAX_MEMORY_POLICY", "allkeys-lru")
        self.redis_connection_timeout = int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5"))
        self.redis_retry_on_timeout = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        self.redis_health_check_interval = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes

    async def _init_redis(self):
        """Initialize Redis connection and vector store with optimized settings"""
        if not self.redis_client:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self.redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=self.redis_connection_timeout,
                    retry_on_timeout=self.redis_retry_on_timeout,
                    health_check_interval=self.redis_health_check_interval
                )
                
                # Configure Redis memory settings
                await self._configure_redis_memory()
                
                self.vector_store = RedisVectorStore(
                    redis_client=self.redis_client,
                    prefix="rag:",
                    index_name="documents",
                    distance_metric="cosine",  # Optimized for semantic search
                    dimension=768  # Standard embedding dimension
                )
                
                logger.info("Redis connection initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {str(e)}")
                raise

    async def _configure_redis_memory(self):
        """Configure Redis memory settings"""
        try:
            # Set max memory
            await self.redis_client.config_set("maxmemory", self.redis_max_memory)
            # Set memory policy
            await self.redis_client.config_set("maxmemory-policy", self.redis_max_memory_policy)
            # Enable AOF for persistence
            await self.redis_client.config_set("appendonly", "yes")
            # Set AOF fsync policy
            await self.redis_client.config_set("appendfsync", "everysec")
            # Enable RDB for backup
            await self.redis_client.config_set("save", "900 1 300 10 60 10000")
            
            logger.info("Redis memory configuration applied successfully")
        except Exception as e:
            logger.error(f"Failed to configure Redis memory: {str(e)}")
            # Continue without memory configuration

    async def _close_redis(self):
        """Close Redis connection with proper cleanup"""
        if self.redis_client:
            try:
                # Save data before closing
                await self.redis_client.save()
                await self.redis_client.close()
                self.redis_client = None
                logger.info("Redis connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {str(e)}")

    def _get_cache_key(self, query: str) -> str:
        """Generate a cache key for a query with namespace"""
        return f"rag:response:{hashlib.md5(query.encode()).hexdigest()}"

    async def _get_cached_response(self, query: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(query)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                if datetime.fromisoformat(data["expires_at"]) > datetime.now():
                    # Update last accessed time
                    await self.redis_client.expire(cache_key, self.response_cache_ttl)
                    return data["response"]
                else:
                    # Clean up expired cache
                    await self.redis_client.delete(cache_key)
        except Exception as e:
            logger.error(f"Error retrieving cached response: {str(e)}")
        return None

    async def _cache_response(self, query: str, response: str):
        """Cache response with expiration and compression"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(query)
            expires_at = datetime.now() + timedelta(seconds=self.response_cache_ttl)
            
            data = {
                "response": response,
                "expires_at": expires_at.isoformat(),
                "cached_at": datetime.now().isoformat()
            }
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                await pipe.setex(
                    cache_key,
                    self.response_cache_ttl,
                    json.dumps(data)
                )
                # Add to sorted set for cache statistics
                await pipe.zadd(
                    "rag:cache:stats",
                    {cache_key: datetime.now().timestamp()}
                )
                await pipe.execute()
                
            logger.debug(f"Cached response for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")

    async def _cleanup_old_cache(self):
        """Clean up old cache entries"""
        if not self.redis_client:
            return
            
        try:
            # Remove entries older than 24 hours from stats
            cutoff = datetime.now().timestamp() - 86400
            await self.redis_client.zremrangebyscore("rag:cache:stats", 0, cutoff)
            
            # Get cache size
            cache_size = await self.redis_client.dbsize()
            if cache_size > 10000:  # Arbitrary limit
                # Remove oldest entries if cache is too large
                await self.redis_client.zremrangebyrank("rag:cache:stats", 0, 1000)
                logger.info("Cleaned up old cache entries")
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")

    @step
    async def ingest(self, ctx: Context, ev: StartEvent) -> StopEvent | None:
        """Entry point to ingest documents from a directory."""
        dirname = ev.get("dirname")
        if not dirname:
            return None

        await self._init_redis()
        
        # Optimized text splitting configuration
        text_splitter = TokenTextSplitter(
            chunk_size=256,  # Smaller chunks for better semantic meaning
            chunk_overlap=32,  # Reduced overlap for efficiency
            separator="\n\n"  # Split on paragraphs
        )
        
        node_parser = SimpleNodeParser.from_defaults(
            text_splitter=text_splitter
        )
        
        # Load documents with optimized chunking
        documents = SimpleDirectoryReader(
            dirname,
            file_extnames=[".txt", ".md", ".pdf"],  # Specify supported file types
            exclude_hidden=True  # Skip hidden files
        ).load_data()
        
        # Use Redis for vector storage
        storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        
        self.index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=storage_context,
            node_parser=node_parser,
            show_progress=True
        )
        
        return StopEvent(result=self.index)

    @step
    async def retrieve(self, ctx: Context, ev: StartEvent) -> RetrieverEvent | None:
        """Entry point for RAG retrieval."""
        query = ev.get("query")
        index = ev.get("index") or self.index

        if not query:
            return None

        if index is None:
            print("Index is empty, load some documents before querying!")
            return None

        # Check cache first
        cached_response = await self._get_cached_response(query)
        if cached_response:
            return RetrieverEvent(nodes=[NodeWithScore(node=None, score=1.0, text=cached_response)])

        # Use cached embeddings if available
        retriever = index.as_retriever(
            similarity_top_k=3,  # Increased for better context
            streaming=True,  # Enable streaming for better memory usage
            filters={"score_threshold": 0.7}  # Only return relevant results
        )
        
        nodes = await retriever.aretrieve(query)
        await ctx.set("query", query)
        return RetrieverEvent(nodes=nodes)

    @step
    async def synthesize(self, ctx: Context, ev: RetrieverEvent) -> StopEvent:
        """Generate a response using retrieved nodes."""
        # If we have a cached response, return it directly
        if len(ev.nodes) == 1 and ev.nodes[0].node is None:
            return StopEvent(result=ev.nodes[0].text)

        summarizer = CompactAndRefine(
            streaming=True,
            verbose=True,
            max_tokens=512,  # Limit response size
            structured_answer_filtering=True  # Enable structured answer filtering
        )
        query = await ctx.get("query", default=None)
        response = await summarizer.asynthesize(query, nodes=ev.nodes)
        
        # Cache the response
        if query:
            await self._cache_response(query, response)
            
        return StopEvent(result=response)

    async def query(self, query_text: str):
        """Helper method to perform a complete RAG query."""
        if self.index is None:
            raise ValueError("No documents have been ingested. Call ingest_documents first.")
        
        try:
            result = await self.run(query=query_text, index=self.index)
            return result
        finally:
            await self._close_redis()

    async def ingest_documents(self, directory: str):
        """Helper method to ingest documents."""
        try:
            result = await self.run(dirname=directory)
            self.index = result
            return result
        finally:
            await self._close_redis()

# Example usage
async def main():
    # Initialize the workflow
    workflow = RAGWorkflow()
    
    # Ingest documents
    await workflow.ingest_documents("data")
    
    # Perform a query
    result = await workflow.query("How was DeepSeekR1 trained?")
    
    # Print the response
    async for chunk in result.async_response_gen():
        print(chunk, end="", flush=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 