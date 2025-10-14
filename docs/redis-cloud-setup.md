# Redis Cloud - Guide de Configuration Production
> Dernière mise à jour: 12 octobre 2025  
> Tâche: P1.3.2  
> Temps estimé: 30 minutes

---

## 🎯 OBJECTIF

Configurer une instance Redis Cloud production pour MCP avec:
- Cache strategy optimisée
- TLS activé
- Monitoring
- Auto-scaling

---

## 📋 ÉTAPE 1 : CRÉER L'INSTANCE (10 min)

### Option A : Redis Cloud (Recommandé)

1. **Créer un compte** : https://redis.com/try-free/
2. **Créer une database** :

```yaml
Cloud Provider: AWS
Region: eu-west-1 (Frankfurt)
  - Proche du serveur MCP
  - Latency < 10ms

Plan: Fixed (30MB Free) → Upgrade to 250MB
Price: ~$10/mois

Database Name: mcp-cache

Options:
  - Eviction Policy: allkeys-lru (LRU sur toutes les clés)
  - Data Persistence: AOF every 1 sec
  - TLS: Enabled
```

### Option B : Upstash (Alternative)

1. **Créer un compte** : https://upstash.com/
2. **Créer une database** :

```yaml
Type: Regional
Region: eu-west-1

Plan: Pay as you go
  - €0.20 per 100K commands
  - Max connections: 1000
  - TLS: Enabled

Database Name: mcp-cache
```

---

## 📋 ÉTAPE 2 : CONFIGURATION (5 min)

### 2.1 Récupérer Connection String

**Redis Cloud** :
1. Databases → mcp-cache → Configuration
2. Copier: "Public endpoint"

Format:
```
redis-12345.c123.eu-west-1-1.ec2.cloud.redislabs.com:12345
```

3. Password: Depuis "Security" tab

**Connection String complète** :
```
rediss://default:YOUR_PASSWORD@redis-12345.c123.eu-west-1-1.ec2.cloud.redislabs.com:12345
```

### 2.2 Configuration Avancée (optionnel)

**Eviction Policy** :
- Recommandé: `allkeys-lru`
- Alternative: `volatile-lru` (si TTL explicites)

**Max Memory** :
- Set à 80% de la RAM disponible
- Exemple: 250MB → maxmemory 200MB

**Persistence** :
- AOF (Append Only File): Every 1 sec
- RDB snapshot: Every 5 min

---

## 📋 ÉTAPE 3 : CACHE STRATEGY (5 min)

### 3.1 TTL par Type de Données

Créer un fichier de config :

```python
# config/redis_cache_strategy.py

CACHE_TTL = {
    # Node data (change peu fréquemment)
    "node_data": 300,  # 5 minutes
    
    # Channel data (peut changer)
    "channel_data": 600,  # 10 minutes
    
    # Metrics (temps réel)
    "metrics": 60,  # 1 minute
    
    # Scores (recalculés périodiquement)
    "channel_scores": 900,  # 15 minutes
    "node_scores": 1800,  # 30 minutes
    
    # Network graph (peu volatile)
    "network_graph": 21600,  # 6 heures
    "network_stats": 3600,  # 1 heure
    
    # Heavy queries (rapports)
    "analytics_query": 1800,  # 30 minutes
    "dashboard_data": 300,  # 5 minutes
    
    # Temporary data
    "rate_limit": 60,  # 1 minute
    "session": 3600,  # 1 heure
}

# Préfixes pour organisation
CACHE_PREFIXES = {
    "node": "node:",
    "channel": "ch:",
    "score": "score:",
    "metric": "metric:",
    "graph": "graph:",
    "query": "query:",
    "session": "sess:"
}
```

### 3.2 Exemple d'Utilisation

```python
from redis import Redis
from config.redis_cache_strategy import CACHE_TTL, CACHE_PREFIXES

# Connexion
redis_client = Redis.from_url(os.getenv("REDIS_URL"))

# Cache node data
key = f"{CACHE_PREFIXES['node']}{node_id}"
redis_client.setex(
    key,
    CACHE_TTL['node_data'],
    json.dumps(node_data)
)

# Récupérer
cached = redis_client.get(key)
if cached:
    node_data = json.loads(cached)
```

---

## 📋 ÉTAPE 4 : METTRE À JOUR .ENV (5 min)

Sur le serveur MCP :

```bash
nano .env
```

**Ajouter** :

```bash
# Redis Cloud
REDIS_URL=rediss://default:YOUR_PASSWORD@redis-12345.c123.eu-west-1-1.ec2.cloud.redislabs.com:12345
REDIS_MAX_CONNECTIONS=50
REDIS_TIMEOUT=5
REDIS_DECODE_RESPONSES=true

# Cache TTL (secondes)
CACHE_NODE_DATA_TTL=300
CACHE_CHANNEL_DATA_TTL=600
CACHE_METRICS_TTL=60
CACHE_SCORES_TTL=900
CACHE_HEAVY_QUERIES_TTL=1800
```

---

## ✅ ÉTAPE 5 : VALIDATION (5 min)

### Test de Connexion

```bash
python3 << 'PYEOF'
import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Connexion
r = redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True
)

try:
    # Test ping
    r.ping()
    print("✅ Connexion Redis réussie!")
    
    # Test set/get
    r.setex("test_key", 10, "test_value")
    value = r.get("test_key")
    print(f"✅ Set/Get test: {value}")
    
    # Test info
    info = r.info()
    print(f"Redis version: {info['redis_version']}")
    print(f"Connected clients: {info['connected_clients']}")
    print(f"Used memory: {info['used_memory_human']}")
    
    # Cleanup
    r.delete("test_key")
    print("✅ Tous tests réussis!")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
finally:
    r.close()
PYEOF
```

**Attendu** :
```
✅ Connexion Redis réussie!
✅ Set/Get test: test_value
Redis version: 7.2.x
Connected clients: 1
Used memory: 1.23M
✅ Tous tests réussis!
```

---

## 📊 RÉSUMÉ

### Configuration Finale

```yaml
Provider: Redis Cloud
Instance: mcp-cache
Region: AWS eu-west-1
Size: 250MB
Price: ~$10/mois

Features:
  - TLS: Enabled
  - Persistence: AOF + RDB
  - Eviction: allkeys-lru
  - Max Memory: 200MB

Performance:
  - Latency: < 10ms
  - Throughput: 10K ops/sec
  - Connections: 50 max
```

### Connection String

```bash
REDIS_URL=rediss://default:PASSWORD@redis-12345...com:12345
```

### Cache Strategy

```
Total TTLs définis: 10 types
Shortest: 60s (metrics)
Longest: 6h (network graph)
Average: ~30 min
```

---

## 🎯 CHECKLIST

- [ ] Compte Redis Cloud créé
- [ ] Instance créée (250MB, eu-west-1)
- [ ] TLS activé
- [ ] Eviction policy: allkeys-lru
- [ ] Connection string récupérée
- [ ] Password sécurisé
- [ ] .env mis à jour
- [ ] Test de connexion réussi
- [ ] Test set/get validé

---

## 📈 MONITORING

### Métriques à Surveiller

```yaml
Performance:
  - Hit rate: Target >85%
  - Latency: Target <10ms p95
  - Throughput: ops/sec
  
Resources:
  - Memory usage: <80%
  - Connections: <80% max
  - Network I/O
  
Errors:
  - Connection errors
  - Timeouts
  - Evictions (trop fréquentes = augmenter taille)
```

### Dashboard Redis Cloud

- Metrics tab : Graphiques temps réel
- Slow Log : Commandes lentes
- Latency : Par région

---

## 🆘 TROUBLESHOOTING

### Erreur: Connection refused

```
Vérifier:
1. TLS activé (rediss:// pas redis://)
2. Port correct (affiché dans console)
3. Firewall/Security groups
```

### Erreur: Authentication failed

```
Vérifier:
1. Password correct
2. Username (default pour Redis Cloud)
```

### Performance dégradée

```
Actions:
1. Vérifier hit rate (<85% = problème)
2. Analyser slow log
3. Augmenter taille si memory > 80%
4. Ajuster TTL si evictions fréquentes
```

---

## 📞 SUPPORT

- **Redis Cloud** : https://redis.com/redis-enterprise-cloud/support/
- **Upstash** : https://upstash.com/docs
- **Pricing** : https://redis.com/redis-enterprise-cloud/pricing/

---

**Configuration terminée !** ✅  
**Prochaine étape** : Tester avec l'application MCP

---

*Guide créé le 12 octobre 2025*

