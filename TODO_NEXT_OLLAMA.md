# 📋 TODO: Prochaines étapes Ollama/RAG

> Ce qui reste à faire pour une intégration RAG complète en production

## ✅ Phase 1: Intégration Core — TERMINÉE

- [x] Client Ollama avec retry et streaming
- [x] Adaptateur RAG avec fallback automatique
- [x] Configuration complète
- [x] Intégration dans RAGWorkflow
- [x] Service Docker Ollama
- [x] Script d'initialisation des modèles
- [x] Tests unitaires (29 tests)
- [x] Documentation complète

## 🔄 Phase 2: Tests d'intégration — À FAIRE

### Tests E2E
- [ ] `tests/integration/test_rag_ollama_e2e.py`
  - Test RAG complet: embed → retrieve → generate
  - Test avec vrai service Ollama
  - Test du fallback 8B
  - Test du streaming
  - Snapshots sur temperature=0

### Fixtures
- [ ] Fixture Docker Compose pour tests
- [ ] Fixture données de test (documents Lightning)
- [ ] Mock Ollama pour CI/CD (optionnel)

**Priorité:** 🔴 **HAUTE**  
**Durée estimée:** 2-3h

---

## 🔍 Phase 3: Index vectoriel (RediSearch HNSW) — À FAIRE

### Implémentation
- [ ] Créer index HNSW dans Redis
  - `FT.CREATE idx:routing:v{version} ...`
  - DIM=768, METRIC=COSINE
  - Champs: `uid`, `ts`, `lang`, `embed_version`, `vec`

- [ ] Alias pour index courant
  - `idx:routing:current` → `idx:routing:v{EMBED_VERSION}`

- [ ] Opérations CRUD
  - `add_document(uid, embedding, metadata)`
  - `search_similar(query_embedding, k=8, filters)`
  - `delete_document(uid)`

### Script de réindexation
- [ ] `scripts/reindex.py`
  - Lecture documents depuis MongoDB
  - Génération embeddings avec Ollama
  - Insertion dans index shadow
  - Cutover alias après validation
  - Purge cache Redis

**Priorité:** 🟡 **MOYENNE**  
**Durée estimée:** 4-5h

---

## 📊 Phase 4: Observabilité — À FAIRE

### Métriques Prometheus
- [ ] Ajouter client Prometheus
- [ ] Métriques embeddings
  - `rag_ollama_embed_latency_ms`
  - `rag_ollama_embed_errors_total`
- [ ] Métriques génération
  - `rag_ollama_generate_latency_ms`
  - `rag_ollama_tokens_generated_total`
  - `rag_ollama_fallback_total`
- [ ] Métriques retrieval
  - `rag_retrieval_latency_ms`
  - `rag_retrieval_score_max`
  - `rag_cache_hit_ratio`

### Traces OpenTelemetry
- [ ] Initialiser exporter OTel
- [ ] Spans pour chaque étape RAG
  - `rag.embed`
  - `rag.search`
  - `rag.rerank`
  - `rag.generate`
  - `rag.fallback`

### Dashboard Grafana
- [ ] Panneau latences RAG (p50, p95, p99)
- [ ] Panneau taux d'erreurs
- [ ] Panneau cache hit rate
- [ ] Panneau fallback rate
- [ ] Panneau scores de confiance

**Priorité:** 🟡 **MOYENNE**  
**Durée estimée:** 3-4h

---

## 🔐 Phase 5: Sécurité et API — À FAIRE

### Endpoints API versionnés
- [ ] `POST /v1/ingest` — Ingestion de documents
- [ ] `POST /v1/embed` — Génération embeddings
- [ ] `POST /v1/retrieve` — Recherche vectorielle
- [ ] `POST /v1/generate` — Génération avec contexte
- [ ] `POST /v1/rag` — Pipeline complet

### Schémas Pydantic
- [ ] `IngestRequest`, `IngestResponse`
- [ ] `EmbedRequest`, `EmbedResponse`
- [ ] `RetrieveRequest`, `RetrieveResponse`
- [ ] `GenerateRequest`, `GenerateResponse`
- [ ] `RagRequest`, `RagResponse`

### Sécurité
- [ ] Header `X-API-Version` obligatoire
- [ ] Auth Bearer + validation
- [ ] Rate limiting (60 req/min)
- [ ] WAF simple contre prompt injection
- [ ] Logs masquage données sensibles

**Priorité:** 🟡 **MOYENNE**  
**Durée estimée:** 4-5h

---

## 📈 Phase 6: Évaluation et production — À FAIRE

### Jeu d'évaluation
- [ ] Créer dataset 50-200 questions Lightning (FR/EN)
- [ ] Questions + réponses attendues + sources
- [ ] Métriques: recall@5, recall@10, exact_match

### Validation
- [ ] Script `scripts/evaluate_rag.py`
- [ ] Recall@5 ≥ 0.8 requis
- [ ] Latence retrieval p95 ≤ 2.5s
- [ ] Latence génération p95 ≤ 10s

### Shadow Mode
- [ ] Mode observation (logs uniquement, pas de changements)
- [ ] Durée: 21 jours minimum
- [ ] Analyse quotidienne: erreurs, latences, recall
- [ ] Go/No-Go après 21j basé sur critères

### Rollout progressif
- [ ] Phase 1: 10% traffic → monitoring 7j
- [ ] Phase 2: 50% traffic → monitoring 7j
- [ ] Phase 3: 100% traffic → monitoring continu
- [ ] Rollback si taux erreur > 1% ou recall < 0.7

**Priorité:** 🔴 **HAUTE** (après tests E2E)  
**Durée estimée:** 2-3 semaines

---

## 🎯 Ordre recommandé d'exécution

1. **Tests d'intégration E2E** (2-3h) — Valider que tout fonctionne
2. **Évaluation initiale** (1j) — Dataset + benchmark baseline
3. **Index vectoriel RediSearch** (4-5h) — Performance retrieval
4. **Observabilité** (3-4h) — Monitoring et alertes
5. **API versionnée** (4-5h) — Contrats stables
6. **Shadow mode** (21j) — Validation production
7. **Rollout progressif** (21j) — Mise en production contrôlée

**Total estimé:** ~6-8 semaines

---

## 📚 Références

- [Guide d'intégration Ollama](docs/OLLAMA_INTEGRATION_GUIDE.md)
- [Spécification RAG Ollama](docs/core/spec-rag-ollama.md)
- [Roadmap Production MCP v1.0](_SPECS/Roadmap-Production-v1.0.md)
- [Plan MVP](_SPECS/Plan-MVP.md)

---

**Dernière mise à jour:** 16 octobre 2025

