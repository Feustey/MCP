# Phase 2 - Quick Start Guide

## 🚀 Démarrage rapide

### 1. Tests d'intégration

Tester tous les composants de Phase 2 :

```bash
python scripts/test_phase2_integration.py
```

Résultat attendu : **8/8 tests passés** ✅

---

### 2. Configuration

#### a) Decision Engine

Éditer `config/decision_thresholds.yaml` :

```yaml
# Choisir profil: conservative, aggressive, balanced
active_profile: "balanced"

# Ou personnaliser les poids
weights:
  centrality: 0.20
  liquidity: 0.25
  activity: 0.20
  # ...
```

#### b) Variables d'environnement

```bash
# Ajouter au .env
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_API_KEY=your_api_key_here

# Générer clé de chiffrement macaroon
MACAROON_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# MongoDB (optionnel, fallback local si absent)
MONGODB_URI=mongodb://localhost:27017
```

---

### 3. Usage basique

#### Évaluer un canal

```python
from src.optimizers.decision_engine import DecisionEngine

engine = DecisionEngine()

channel = {
    "channel_id": "123456x789x0",
    "local_balance": 5000000,
    "remote_balance": 5000000,
    "capacity": 10000000,
    "policy": {
        "base_fee_msat": 1000,
        "fee_rate_ppm": 500
    }
}

node_data = {"node_id": "...", "channels": [channel]}

evaluation = engine.evaluate_channel(channel, node_data)

print(f"Décision: {evaluation['decision']}")
print(f"Confiance: {evaluation['confidence']}")
print(f"Reasoning: {evaluation['reasoning']}")
```

#### Appliquer une policy (dry-run)

```python
from src.clients.lnbits_client import LNBitsClient
from src.tools.policy_executor import PolicyExecutor

lnbits = LNBitsClient(base_url="...", api_key="...")
executor = PolicyExecutor(lnbits, dry_run=True)  # Simulation

new_policy = {
    "base_fee_msat": 1200,
    "fee_rate_ppm": 600,
    "time_lock_delta": 40
}

result = await executor.apply_policy_change(
    channel,
    new_policy,
    PolicyChangeType.FEE_INCREASE
)

print(f"Success: {result['success']}")
print(f"Dry-run: {result['dry_run']}")
```

#### Rollback manuel

```bash
# CLI
python -m src.tools.rollback_orchestrator rollback \
    --transaction-id abc123 \
    --reason "Test rollback"
```

Ou en Python :

```python
from src.tools.rollback_orchestrator import RollbackOrchestrator

orchestrator = RollbackOrchestrator(tx_manager, backup_manager)

result = await orchestrator.manual_rollback(
    transaction_id="abc123",
    reason="Manual rollback test"
)
```

---

### 4. API REST (Lightning Scoring)

Démarrer l'API :

```bash
uvicorn main:app --reload
```

#### Endpoints disponibles

**Score d'un nœud** :
```bash
curl http://localhost:8000/api/v1/lightning/scores/node/{node_id}
```

**Recommandation canal** :
```bash
curl http://localhost:8000/api/v1/lightning/scores/channel/{channel_id}
```

**Rankings** :
```bash
curl "http://localhost:8000/api/v1/lightning/scores/rankings?page=1&limit=100"
```

**Batch scoring** :
```bash
curl -X POST http://localhost:8000/api/v1/lightning/scores/batch \
  -H "Content-Type: application/json" \
  -d '{"node_ids": ["03abc...", "03def..."], "force": false}'
```

Swagger UI : http://localhost:8000/docs

---

### 5. Synchronisation Network Graph

```python
from src.integrations.network_graph_sync import NetworkGraphSync
from src.clients.lnbits_client import LNBitsClient

lnbits = LNBitsClient(...)
graph_sync = NetworkGraphSync(lnbits, db=mongo_db)

# Sync complète
await graph_sync.full_sync()

# Ou démarrer sync périodique (background)
asyncio.create_task(graph_sync.start_periodic_sync())

# Utiliser le graphe
centrality = graph_sync.get_node_centrality("03abc...", "betweenness")
path = graph_sync.find_shortest_path("03abc...", "03def...")
neighbors = graph_sync.get_node_neighbors("03abc...", hops=2)
```

---

### 6. Transactions & Backups

```python
from src.tools.transaction_manager import TransactionManager
from src.tools.backup_manager import BackupManager

tx_manager = TransactionManager(db=mongo_db, lnbits_client=lnbits)
backup_manager = BackupManager(db=mongo_db)

# Démarrer transaction
tx_id = tx_manager.begin_transaction(
    node_id="...",
    channels=[channel1, channel2],
    operation_type="policy_update"
)

# Appliquer changements...

# Commit ou rollback
if all_ok:
    tx_manager.commit_transaction(tx_id)
else:
    tx_manager.rollback_transaction(tx_id, reason="Erreur détectée")

# Maintenance backups (cron daily)
stats = backup_manager.apply_retention_policy()
backup_manager.cleanup_old_data(days=90)
```

---

## 📚 Documentation complète

- **Architecture** : `PHASE2_COMPLETE_REPORT.md`
- **Roadmap** : `_SPECS/Roadmap-Production-v1.0.md`
- **API** : http://localhost:8000/docs (Swagger)
- **Code** : Docstrings dans chaque module

---

## 🐛 Troubleshooting

### Erreur "MongoDB non disponible"

➡️ **Solution** : Les modules fonctionnent en mode local si MongoDB n'est pas configuré. Vérifier `MONGODB_URI` dans `.env`.

### Erreur "MACAROON_ENCRYPTION_KEY non défini"

➡️ **Solution** :
```bash
export MACAROON_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Rate limit atteint

➡️ **Solution** : Le client LNBits limite à 100 req/min par défaut. Modifier `rate_limit_requests` dans `LNBitsClient.__init__()`.

### Validation policy échoue

➡️ **Solution** : Vérifier les limites dans `config/decision_thresholds.yaml` section `safety_limits`. Utiliser `force=True` pour bypasser (avec prudence).

---

## 🔧 Mode Production

Pour activer le mode production (exécution réelle) :

```python
# Désactiver dry-run
executor = PolicyExecutor(lnbits, dry_run=False)  # ⚠️ ATTENTION

# Activer notifications
orchestrator = RollbackOrchestrator(
    tx_manager, 
    backup_manager,
    telegram_client=telegram  # Pour alertes
)
```

**⚠️ IMPORTANT** : Toujours tester en dry-run d'abord !

---

## 📞 Support

- **Bugs** : Vérifier logs (niveau DEBUG)
- **Questions** : Consulter docstrings + `PHASE2_COMPLETE_REPORT.md`
- **Configuration** : `config/decision_thresholds.yaml`

---

**Happy optimizing! ⚡️**

