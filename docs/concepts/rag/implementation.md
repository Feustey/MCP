# Implémentation du RAG

Ce document détaille l'implémentation technique du système RAG.

## Structure du Projet

```
src/
├── rag/
│   ├── __init__.py
│   ├── core.py
│   ├── vector_store.py
│   ├── cache.py
│   ├── llm.py
│   └── utils.py
├── models/
│   ├── __init__.py
│   ├── document.py
│   └── response.py
└── config.py
```

## Composants Principaux

### 1. Core RAG

```python
from typing import List, Optional
from src.models import Document, Response

class AugmentedRAG:
    def __init__(
        self,
        vector_store: VectorStore,
        cache: Cache,
        llm: LLMService
    ):
        self.vector_store = vector_store
        self.cache = cache
        self.llm = llm

    async def query(
        self,
        query: str,
        top_k: int = 5
    ) -> Response:
        # Récupération du contexte
        context = await self._retrieve_context(query, top_k)
        
        # Génération de la réponse
        response = await self._generate_response(query, context)
        
        return response

    async def _retrieve_context(
        self,
        query: str,
        top_k: int
    ) -> List[Document]:
        # Vérification du cache
        cached = await self.cache.get(query)
        if cached:
            return cached

        # Recherche vectorielle
        results = await self.vector_store.search(
            query=query,
            top_k=top_k
        )

        # Mise en cache
        await self.cache.set(query, results)
        
        return results

    async def _generate_response(
        self,
        query: str,
        context: List[Document]
    ) -> Response:
        # Préparation du contexte
        prepared_context = self._prepare_context(context)
        
        # Génération
        response = await self.llm.generate(
            query=query,
            context=prepared_context
        )
        
        return response
```

### 2. Vector Store

```python
from qdrant_client import QdrantClient
from src.models import Document

class VectorStore:
    def __init__(self, client: QdrantClient):
        self.client = client

    async def search(
        self,
        query: str,
        top_k: int
    ) -> List[Document]:
        # Génération de l'embedding
        embedding = await self._generate_embedding(query)
        
        # Recherche
        results = await self.client.search(
            collection_name="documents",
            query_vector=embedding,
            limit=top_k
        )
        
        return [Document.from_dict(r) for r in results]
```

### 3. Cache

```python
from redis import Redis
from typing import Optional, Any

class Cache:
    def __init__(self, client: Redis):
        self.client = client

    async def get(self, key: str) -> Optional[Any]:
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> None:
        await self.client.set(
            key,
            value,
            ex=ttl
        )
```

### 4. LLM Service

```python
from openai import AsyncOpenAI
from src.models import Response

class LLMService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate(
        self,
        query: str,
        context: str
    ) -> Response:
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": query}
            ]
        )
        
        return Response(
            text=response.choices[0].message.content
        )
```

## Tests

```python
import pytest
from src.rag import AugmentedRAG

@pytest.mark.asyncio
async def test_rag_query():
    rag = AugmentedRAG(...)
    
    response = await rag.query(
        "Quelle est la performance du canal X ?"
    )
    
    assert response.text is not None
    assert len(response.text) > 0
```

## Déploiement

### Configuration Docker

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "src.rag"]
```

### Configuration Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: rag
        image: rag-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: VECTOR_DB_URL
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: vector-db-url
```

## Prochaines Étapes

- [Best Practices](../../guides/best-practices/rag-best-practices.md)
- [Troubleshooting](../../guides/troubleshooting.md) 