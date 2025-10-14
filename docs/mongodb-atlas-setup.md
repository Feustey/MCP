# MongoDB Atlas - Guide de Configuration Production
> Dernière mise à jour: 12 octobre 2025  
> Tâche: P1.3.1  
> Temps estimé: 45 minutes

---

## 🎯 OBJECTIF

Configurer un cluster MongoDB Atlas production-ready pour MCP avec:
- Collections et indexes optimisés
- Backup automatique
- Monitoring actif
- Sécurité renforcée

---

## 📋 ÉTAPE 1 : CRÉER LE CLUSTER (10 min)

### 1.1 Créer un Compte

1. Aller sur https://www.mongodb.com/cloud/atlas/register
2. S'inscrire avec email professionnel
3. Vérifier l'email

### 1.2 Créer le Cluster

**Configuration recommandée** :

```yaml
Cluster Tier: M10 (Production)
  - RAM: 2 GB
  - Storage: 10 GB
  - Price: ~$60/mois
  
Cloud Provider: AWS
Region: eu-west-1 (Frankfurt)
  - Proche du serveur (147.79.101.32)
  - Latency < 50ms

Cluster Name: mcp-prod-cluster

MongoDB Version: 7.0 (latest stable)
```

**Étapes** :
1. Build a Database → Shared (pour M10)
2. Provider: AWS, Region: eu-west-1
3. Cluster Tier: M10
4. Cluster Name: `mcp-prod-cluster`
5. Create Deployment

⏳ **Attendre 5-10 minutes** pour le provisioning

---

## 📋 ÉTAPE 2 : CONFIGURER LA SÉCURITÉ (5 min)

### 2.1 Créer un Utilisateur Database

1. Security → Database Access → Add New Database User

**Configuration** :
```yaml
Authentication Method: Password
Username: mcp_user
Password: <générer un mot de passe fort>
  
Database User Privileges:
  - Built-in Role: Atlas admin
  OU
  - Custom Role:
      - readWrite sur database 'mcp_prod'
      - dbAdmin sur database 'mcp_prod'
```

🔐 **Sauvegarder** le mot de passe dans un gestionnaire sécurisé !

### 2.2 Configurer Network Access

1. Security → Network Access → Add IP Address

**Options** :
```yaml
Option 1 (Recommandée):
  - Add Current IP Address
  - Add Server IP: 147.79.101.32
  - Comment: "MCP Production Server"

Option 2 (Développement):
  - Allow Access from Anywhere (0.0.0.0/0)
  - ⚠️ À restreindre en production !
```

---

## 📋 ÉTAPE 3 : CRÉER LA BASE & COLLECTIONS (10 min)

### 3.1 Connection String

1. Database → Connect → Drivers
2. Driver: Python, Version: 4.5 ou later
3. Copier la connection string:

```
mongodb+srv://mcp_user:<password>@mcp-prod-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

### 3.2 Se Connecter via MongoDB Compass (optionnel)

1. Télécharger : https://www.mongodb.com/products/compass
2. Coller la connection string
3. Remplacer `<password>` par le vrai mot de passe
4. Connect

### 3.3 Créer la Base de Données

```javascript
// Dans Compass ou mongosh
use mcp_prod;
```

### 3.4 Créer les Collections avec Indexes

```javascript
// Collection: nodes
db.createCollection("nodes");
db.nodes.createIndex({ "node_id": 1 }, { unique: true });
db.nodes.createIndex({ "created_at": -1 });
db.nodes.createIndex({ "pubkey": 1 });

// Collection: channels
db.createCollection("channels");
db.channels.createIndex({ "channel_id": 1 }, { unique: true });
db.channels.createIndex({ "node_id": 1, "created_at": -1 });
db.channels.createIndex({ "peer_pubkey": 1 });
db.channels.createIndex({ "capacity": -1 });

// Collection: policies
db.createCollection("policies");
db.policies.createIndex({ "channel_id": 1, "applied_at": -1 });
db.policies.createIndex({ "created_at": -1 });

// Collection: metrics
db.createCollection("metrics");
db.metrics.createIndex({ "node_id": 1, "timestamp": -1 });
db.metrics.createIndex({ "channel_id": 1, "timestamp": -1 });
db.metrics.createIndex({ "timestamp": -1 }, { expireAfterSeconds: 7776000 }); // 90 jours

// Collection: decisions
db.createCollection("decisions");
db.decisions.createIndex({ "node_id": 1, "decision_type": 1, "created_at": -1 });
db.decisions.createIndex({ "channel_id": 1, "created_at": -1 });
db.decisions.createIndex({ "created_at": -1 });

// Collection: policy_backups
db.createCollection("policy_backups");
db.policy_backups.createIndex({ "backup_id": 1 }, { unique: true });
db.policy_backups.createIndex({ "channel_id": 1, "created_at": -1 });
db.policy_backups.createIndex({ "created_at": -1 });
db.policy_backups.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 }); // Auto-cleanup

// Collection: macaroons
db.createCollection("macaroons");
db.macaroons.createIndex({ "id": 1 }, { unique: true });
db.macaroons.createIndex({ "metadata.created_at": -1 });
db.macaroons.createIndex({ "metadata.revoked": 1, "metadata.expires_at": 1 });

// Collection: shadow_decisions (pour shadow mode)
db.createCollection("shadow_decisions");
db.shadow_decisions.createIndex({ "decision_id": 1 }, { unique: true });
db.shadow_decisions.createIndex({ "channel_id": 1, "timestamp": -1 });
db.shadow_decisions.createIndex({ "timestamp": -1 });
```

---

## 📋 ÉTAPE 4 : CONFIGURER LES BACKUPS (5 min)

1. Database → Backup → Configure

**Configuration** :
```yaml
Backup Frequency: Daily
Retention: 7 days
Backup Window: 02:00 - 04:00 UTC (Europe)

Point-in-Time Restore: Enabled (optionnel, +$5/mois)
```

---

## 📋 ÉTAPE 5 : ACTIVER LE MONITORING (5 min)

1. Database → Metrics

**Alertes recommandées** :
```yaml
Alerts to Enable:
  - Connections > 80% of max
  - Disk usage > 80%
  - Replication lag > 10s
  - Query execution time > 1s
  
Alert Channels:
  - Email: votre@email.com
  - Slack: (optionnel)
```

---

## 📋 ÉTAPE 6 : METTRE À JOUR .ENV (5 min)

Sur le serveur MCP :

```bash
# Se connecter
ssh feustey@147.79.101.32
cd /home/feustey/mcp-production

# Éditer .env
nano .env
```

**Ajouter/Modifier** :

```bash
# MongoDB Atlas
MONGODB_URL=mongodb+srv://mcp_user:YOUR_PASSWORD@mcp-prod-cluster.xxxxx.mongodb.net/mcp_prod?retryWrites=true&w=majority
MONGODB_DATABASE=mcp_prod
MONGODB_CONNECTION_POOL_SIZE=50
MONGODB_TIMEOUT_MS=5000
```

**Remplacer** :
- `YOUR_PASSWORD` → Le vrai mot de passe
- `xxxxx` → Le cluster ID réel

**Sauvegarder** : Ctrl+X, Y, Enter

---

## ✅ ÉTAPE 7 : VALIDATION (5 min)

### Test de Connexion

```bash
# Test depuis le serveur
python3 << 'PYEOF'
from pymongo import MongoClient
import os

# Charger .env
from dotenv import load_dotenv
load_dotenv()

# Connexion
client = MongoClient(os.getenv("MONGODB_URL"))

# Test
try:
    # Ping
    client.admin.command('ping')
    print("✅ Connexion MongoDB réussie!")
    
    # Lister databases
    print(f"Databases: {client.list_database_names()}")
    
    # Lister collections
    db = client[os.getenv("MONGODB_DATABASE")]
    print(f"Collections: {db.list_collection_names()}")
    
    # Test write
    db.test.insert_one({"test": True})
    db.test.delete_one({"test": True})
    print("✅ Write test réussi!")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
finally:
    client.close()
PYEOF
```

**Attendu** :
```
✅ Connexion MongoDB réussie!
Databases: ['mcp_prod', 'admin', 'local']
Collections: ['nodes', 'channels', 'policies', ...]
✅ Write test réussi!
```

---

## 📊 RÉSUMÉ

### Configuration Finale

```yaml
Cluster: mcp-prod-cluster
Tier: M10 (2GB RAM, 10GB storage)
Region: AWS eu-west-1
Price: ~$60/mois

Database: mcp_prod
Collections: 7 (nodes, channels, policies, etc.)
Indexes: 20+ (optimisés)

Backup: Daily, 7 days retention
Monitoring: Enabled avec alertes

User: mcp_user
Permissions: readWrite + dbAdmin
```

### Connection String

```bash
MONGODB_URL=mongodb+srv://mcp_user:PASSWORD@mcp-prod-cluster.xxxxx.mongodb.net/mcp_prod
```

---

## 🎯 CHECKLIST

- [ ] Compte Atlas créé
- [ ] Cluster M10 créé (eu-west-1)
- [ ] Utilisateur database créé
- [ ] IP serveur whitelistée
- [ ] Base `mcp_prod` créée
- [ ] 7 collections créées
- [ ] 20+ indexes créés
- [ ] Backups configurés (daily)
- [ ] Monitoring activé
- [ ] Connection string dans .env
- [ ] Test de connexion réussi

---

## 🆘 TROUBLESHOOTING

### Erreur: Connection timeout

```
Cause: IP non whitelistée
Solution: Security → Network Access → Add IP
```

### Erreur: Authentication failed

```
Cause: Mauvais username/password
Solution: Vérifier credentials dans .env
```

### Erreur: Database does not exist

```
Cause: Base pas créée
Solution: Utiliser Compass ou mongosh pour créer
```

---

## 📞 SUPPORT

- **Documentation** : https://www.mongodb.com/docs/atlas/
- **Pricing** : https://www.mongodb.com/pricing
- **Support** : Support ticket dans Atlas Console

---

**Configuration terminée !** ✅  
**Prochaine étape** : Configuration Redis Cloud

---

*Guide créé le 12 octobre 2025*

