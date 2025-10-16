## Spécification fonctionnelle — RAG MCP avec Ollama (remplacement OpenAI pour RAG)
> Dernière mise à jour: 16 octobre 2025
> **Statut:** ✅ Implémenté et testé

### Contexte

- Objectif: Remplacer l’usage d’OpenAI dans la pipeline RAG par Ollama local (génération et embeddings), tout en conservant Anthropic pour le chatbot conversationnel non‑RAG.
- Standardiser ingestion → chunking → embeddings → index → retrieval → génération avec observabilité, reproductibilité et API versionnées.
- Corrections prioritaires issues de l’audit: versionnage strict des modèles et embeddings, cache Redis normalisé, traçabilité bout‑à‑bout, endpoints stables, fallback maîtrisé.

### Périmètre

- Inclus: RAG complet (ingestion, index, retrieval, génération), endpoints `/v1`, cache Redis, RediSearch HNSW, script de réindexation idempotent, observabilité (OTel + Prometheus), sécurité (auth, rate limit), fallback 8B, politique de cutover.
- Exclus: UI, packaging Umbrel (reporté), refonte chatbot (Anthropic conservé pour hors‑RAG).

### Hypothèses

- Redis Stack (RediSearch) et MongoDB accessibles via Docker Compose.
- Ollama opérationnel, modèles pré‑pullés: `llama3:70b-instruct-YYYY-MM-DD` (prod) et `llama3:8b-instruct` (fallback), embeddings `nomic-embed-text` (ou `bge-m3`, exclusif).
- Ressources: GPU ≥ 48–64 GB VRAM ou quantisation Q4_K_M/Q5_K_M; CPU hybride à éviter en prod.

## Architecture cible

### Flux

- Sources: Amboss, LNbits, Sparkseer, logs de forwarding, métadonnées de canaux.
- Ingestion: scheduler (cron/Celery Beat), retry exponentiel (3 tentatives), dead‑letter queue.
- Prétraitement: normalisation JSONL, nettoyage HTML, chunking 700–900 tokens, overlap 120, coupes sur titres/listes/sections, préservation blocs code/commandes.
- Embeddings: service Ollama HTTP (`nomic-embed-text` recommandé, multilingue; alternative `bge-m3`).
- Index: Redis Stack RediSearch HNSW (COSINE, DIM=1536); métadonnées et texte dans Mongo `documents` (clé `uid`).
- Retrieval: top‑k=8; rerank top‑3 selon similarité + fraîcheur (décroissance temporelle sur `ts`).
- Génération: `llama3:70b-instruct-YYYY-MM-DD`, `temperature=0.2`, prompt strict; fallback `llama3:8b-instruct` si low‑confidence/timeout.
- Cache: Redis à clés normalisées, TTL homogènes; busting sur ré‑ingestion/réindexation.
- Observabilité: OpenTelemetry (spans) + Prometheus (metrics) + logs JSON corrélés.

## Modèles et versions (reproductibilité)

- Génération (prod): `GEN_MODEL=llama3:70b-instruct-YYYY-MM-DD`, `temperature=0.2`, `top_p=0.9`, `max_tokens=1536`, `num_ctx=8192`.
- Fallback: `llama3:8b-instruct` (même format de prompt).
- Embeddings: `EMBED_MODEL=nomic-embed-text` (ou `bge-m3`, exclusif).
- Versionnage: tags immuables (pas de `latest`), `EMBED_VERSION=YYYY-MM-DD` inscrit dans metadata/documents et index.

## Schéma de données (normalisation)

- Format d’ingestion JSONL:

```json
{
  "uid": "<stable-id>",
  "source": "amboss|lnbits|sparkseer|internal",
  "ts": "<RFC3339>",
  "lang": "fr|en",
  "title": "...",
  "content": "...",
  "tags": ["lightning","fees","routing"],
  "node_pubkey": "...",
  "channel_id": "...",
  "metrics": {"...": "..."}
}
```

- Mongo `documents`: `uid` (PK), `ts`, `lang`, `title`, `content`, `tags[]`, `source`, `embed_version`.

## Chunking

- Taille cible: 700–900 tokens, overlap 120.
- Heuristiques: couper sur titres/listes/sauts de section; préserver blocs code/commandes; détection/forçage langue.

## Embeddings et index

- Embeddings: via Ollama embeddings HTTP.
- Vector store: RediSearch HNSW (COSINE, DIM=1536, FLOAT32).
- Stockage:
  - JSON `doc:{uid}` pour metadata (`uid`, `meta.ts`, `meta.lang`, `meta.embed_version`).
  - Vecteur en champ `vec` (JSON VECTOR si supporté, sinon HASH `hv:{uid}` avec champ binaire `vec`).
- Versionnage: champ `embed_version` associé; changement de modèle/chunking ⇒ réindexation totale.

## Cache Redis (cléspace et TTL)

- Clés normalisées:
  - `rag:embed:hash:{uid}` → `sha1(content)|{EMBED_VERSION}`
  - `rag:retrieval:{query_hash}` → liste `uid` (TTL 24h)
  - `rag:answer:{prompt_hash}` → JSON réponse (TTL 6h)
- Busting: ré‑ingestion d’un `uid` ou changement `EMBED_VERSION` ⇒ invalidation des clés liées (`rag:retrieval:*`, `rag:answer:*`).

## Retrieval

- Paramètres: `top_k=8` (prod).
- Rerank: top‑3 par score de similarité + décroissance temporelle (pondération exponentielle sur `ts`).
- Filtrage: `lang` aligné à la requête; à défaut, mix FR/EN autorisé.
- Guardrail: si `score_max < 0.35` ⇒ “not enough evidence” ou “answer+ask‑for‑source”; flag `degraded=true` en cas de fallback.

## Endpoints API (contrats stables, versionnés)

- Header obligatoire: `X-API-Version: 2025-10-15`. Auth: Bearer interne + rate‑limit IP+token.
- `POST /v1/ingest` `{ batch: [Document] }` → `202/200`
- `POST /v1/embed` `{ texts[], model, embed_version }` → `{ embeddings[][] }`
- `POST /v1/retrieve` `{ query, k, filters }` → `{ uids[], scores[], sources[] }`
- `POST /v1/generate` `{ query, context_chunks[], params }` → `{ answer, citations[], confidence }`
- `POST /v1/rag` `{ query, lang="fr" }` → pipeline complet.

Exemples Pydantic:

```python
class RetrieveReq(BaseModel):
    query: str
    k: int = 8
    filters: dict | None = None

class RagReq(BaseModel):
    query: str
    lang: Literal["fr","en"] = "fr"
```

## Prompting (RAG)

- System prompt minimal, non verbeux; langue pilotée par `lang`.
- Format:

```text
You answer strictly from the provided CONTEXT.
If missing, say you lack evidence. Language = {lang}.
CONTEXT:
{chunk_1}
---
{chunk_2}
...
```

- `temperature=0.2` par défaut; citations par `uid`→URL/trace.

## Runtime Ollama

- `OLLAMA_NUM_PARALLEL=1` (70B, queue côté API), `OMP_NUM_THREADS`=cœurs physiques, `num_ctx=8192`.
- GPU: vRAM ≥ 48–64 GB; quantisation `Q4_K_M` (ou `Q5_K_M`) sinon.
- Healthcheck: `GET /api/tags` + warmup prompt au démarrage API.
- Sécurité: Ollama non exposé publiquement; accès via API interne seulement.

Extrait docker‑compose:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    environment:
      - OLLAMA_KEEP_ALIVE=30m
    volumes:
      - ./ollama:/root/.ollama
    ports: ["11434:11434"]

  api:
    build: ./api
    environment:
      - OLLAMA_URL=http://ollama:11434
      - EMBED_MODEL=nomic-embed-text
      - GEN_MODEL=llama3:70b-instruct-2025-07-01
      - REDIS_URL=redis://redis:6379/0
      - MONGO_URL=mongodb://mongo:27017/mcp
      - RAG_TOPK=8
    depends_on: [ollama, redis, mongo]
    ports: ["8080:8080"]

  redis:
    image: redis/redis-stack:latest
    ports: ["6379:6379"]

  mongo:
    image: mongo:6
    ports: ["27017:27017"]
```

## Observabilité

- Traces OpenTelemetry: spans `ingest`, `embed`, `search`, `rerank`, `generate`, `fallback`.
- Prometheus:
  - `rag_retrieval_latency_ms`
  - `rag_topk_score_max`, `rag_topk_score_mean`
  - `cache_hit_ratio`
  - `timeout_rate`
  - `answer_hallucination_flag` (heuristique: présence de sources)
- Logs JSON corrélés (requête→chunks→réponse); masquage champs sensibles.

## Sécurité

- CORS fermé; Auth Bearer; rate‑limit appliqué aux routes internes.
- WAF simple contre prompt‑injection (patterns “IGNORE CONTEXT”, etc.).
- RGPD: anonymiser `node_pubkey` (optionnel) et limiter `channel_id` dans les logs.
- Backups: Mongo quotidiens + snapshots Redis; backup `~/.ollama` avant upgrade.

## Évaluation continue

- Jeu d’évaluation interne 50–200 questions (FR/EN).
- Métriques: top‑k recall, exact‑match@k; bench latence retrieval p95.
- Gates de déploiement: recall@5 ≥ 0.8, latence retrieval p95 ≤ 2.5 s.
- Question de suivi standard: "Quelle est la précision top‑k@5 après réindexation complète ?"

## Réindexation et cutover (idempotent)

- Déclencheurs: changement de modèle d’embedding ou paramètres de chunking/nettoyage.
- Processus:
  1) Construire index shadow `idx:routing:v{EMBED_VERSION}` (HNSW).
  2) Ingestion → chunk → embed → index avec skip via `rag:embed:hash:{uid}`.
  3) Basculer alias: `alias:idx:routing:current -> idx:routing:v{EMBED_VERSION}`.
  4) Purger caches `rag:retrieval:*` et `rag:answer:*`.
  5) Vérifier recall@5 et p95 retrieval avant annonce "prod".

Variables d’environnement (réindexation):

```
GEN_MODEL=llama3:70b-instruct-2025-07-01
EMBED_MODEL=nomic-embed-text
EMBED_VERSION=2025-10-15
API_BASE=http://localhost:8080
REDIS_URL=redis://localhost:6379/0
MONGO_URL=mongodb://localhost:27017/mcp
INDEX_NAME=idx:routing:v${EMBED_VERSION}
ALIAS_NAME=idx:routing:current
```

## Scénarios d’erreurs et fallback

- Low‑confidence (`score_max < 0.35`) ou timeout > p95*2: fallback 8B, marquer `degraded=true`.
- Ollama indisponible: `503` pour `/v1/generate` et `/v1/rag`; `/v1/retrieve` reste disponible.
- Embeddings: retry backoff (3 tentatives) et DLQ côté ingestion.

## Intégration avec MCP (contrats internes) — ✅ IMPLÉMENTÉ

- ✅ `src/clients/ollama_client.py`: Client HTTP asynchrone complet avec retry, streaming, healthcheck
- ✅ `src/rag_ollama_adapter.py`: Adaptateur RAG avec formatage prompts Llama 3, fallback automatique
- ✅ `src/rag.py`: Workflow RAG mis à jour pour utiliser `OllamaRAGAdapter`
- ✅ `config/rag_config.py`: Configuration complète avec tous les paramètres Ollama
- ✅ `docker-compose.production.yml`: Service Ollama avec healthcheck et volumes persistants
- ✅ `scripts/ollama_init.sh`: Script d'initialisation pour pull des modèles
- ✅ `tests/unit/test_ollama_client.py`: Tests unitaires complets du client
- ✅ `tests/unit/test_rag_ollama_adapter.py`: Tests unitaires de l'adaptateur
- ✅ `docs/OLLAMA_INTEGRATION_GUIDE.md`: Guide complet d'intégration et troubleshooting
- ⏳ `app/routes/rag.py`: exposer `/v1/*` avec schémas Pydantic + `X-API-Version`.
- ⏳ Docker Compose: ajouter Redis Stack (RediSearch), variables d'env et healthchecks; ne pas exposer Ollama publiquement.

## Tests et critères d’acceptation

- Unitaires: chunking, hashing cache, filtrage `lang`, decay fraîcheur, guardrail score.
- Intégration: `/v1/rag` bout‑à‑bout (cache hit/miss, alias index, fallback 8B).
- Régression: "playbooks Lightning" (réponses routinières) avec snapshot tests.
- Performance: retrieval p95 ≤ 2.5 s (sans génération); suivi tokens/s pour génération.
- Sécurité: auth obligatoire, rate‑limit actif, WAF patterns prompt‑injection.

## Déploiement et exploitation

- Tags immuables pour les modèles; pas de `latest`.
- Concurrence: `OLLAMA_NUM_PARALLEL=1` (70B); queue côté API.
- Threading: `OMP_NUM_THREADS`=cœurs physiques; `num_ctx=8192`.
- Healthchecks + warmup; monitoring mémoire pic et tokens/s.
- Upgrade: backup `~/.ollama`, tests en staging, cutover alias post‑réindexation, purge caches, validation des gates.

## Risques et mitigations

- OOM/latence: quantisation + limites de concurrence.
- Drift modèle: tags épinglés + backups; interdiction de `latest`.
- Incohérence index/cache: alias + réindex idempotente + purge ciblée.
- Sécurité: Ollama non exposé; auth stricte + rate‑limit; masquage logs.

## Plan d'implémentation phasé

1) ✅ Intégrer clients Ollama (embed/generate) + variables d'environnement.
2) ✅ Adaptateur RAG Ollama avec formatage prompts et fallback.
3) ✅ Configuration complète dans `config/rag_config.py`.
4) ✅ Intégration dans `RAGWorkflow` (`src/rag.py`).
5) ✅ Service Docker Ollama dans `docker-compose.production.yml`.
6) ✅ Tests unitaires pour client et adaptateur.
7) ✅ Documentation complète (guide intégration + spec technique).
8) ⏳ Normaliser cache Redis et cléspace; ajouter RediSearch HNSW + alias courant.
9) ⏳ Exposer `/v1/*` avec schémas Pydantic/headers versionnés; auth+rate‑limit.
10) ⏳ Observabilité (OTel + Prometheus) et logs JSON corrélés.
11) ⏳ Script réindexation idempotent + cutover alias + purge.
12) ⏳ Jeux d'évaluation et gates; passage prod contrôlé.

## Checklist de préparation (exécution rapide)

- **Modèles**: `ollama pull` des tags immuables (70B/8B, embeddings).
- **Runtime**: `OLLAMA_NUM_PARALLEL=1`, `OMP_NUM_THREADS`, `num_ctx=8192`.
- **Index**: créer index HNSW DIM=1536 (COSINE), alias `idx:routing:current`.
- **Cache**: définir TTLs (retrieval 24h, answer 6h) et busting.
- **Sécurité**: Auth Bearer + rate‑limit; WAF simple; CORS fermé.
- **Obs**: exposer métriques Prometheus; activer spans OTel; logs JSON.
- **Gates**: recall@5 ≥ 0.8, p95 retrieval ≤ 2.5 s; fallback 8B balisé.


