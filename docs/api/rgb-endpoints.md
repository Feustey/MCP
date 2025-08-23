# 🌈 Documentation Complète des Endpoints RGB

> **API RGB pour les smart contracts Bitcoin et les assets RGB++**  
> Dernière mise à jour: 23 août 2025

## 🎯 Vue d'ensemble

Cette documentation présente tous les endpoints RGB intégrés à l'API MCP pour la gestion des smart contracts Bitcoin, des assets RGB++ et des transactions sur le réseau Lightning.

## 🔗 Base URL

```
Production: https://api.dazno.de/api/v1/rgb
Développement: http://localhost:8000/api/v1/rgb
```

## 🔐 Authentification

### Tokens supportés
- **JWT Token** : `Authorization: Bearer <jwt_token>`
- **API Key** : `Authorization: Bearer <api_key>`
- **Mainnet Access** : Token spécial requis pour mainnet

### Permissions
- `read_assets` : Lecture des assets RGB
- `create_assets` : Création d'assets RGB
- `transfer_assets` : Transfert d'assets
- `deploy_contracts` : Déploiement de smart contracts
- `submit_transactions` : Soumission de transactions
- `mainnet_access` : Accès au réseau principal

---

## 📋 Assets RGB

### 1. **Liste des assets** - `GET /api/v1/rgb/assets/list`

Récupère la liste de tous les assets RGB disponibles.

**Paramètres de requête :**
```
limit: int = 50          # Nombre maximum d'assets
offset: int = 0          # Décalage pour pagination  
asset_type: string       # Filtrer par type (token, nft, stablecoin)
```

**Réponse :**
```json
{
  "status": "success",
  "assets": [
    {
      "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
      "name": "DazCoin",
      "symbol": "DAZ",
      "total_supply": 21000000,
      "decimals": 8,
      "type": "token",
      "created_at": "2025-08-23T10:00:00Z",
      "contract_id": "contract_123"
    }
  ],
  "total": 125,
  "limit": 50,
  "offset": 0,
  "timestamp": "2025-08-23T12:00:00Z"
}
```

### 2. **Créer un asset** - `POST /api/v1/rgb/assets/create`

Crée un nouvel asset RGB avec smart contract.

**Permission requise :** `create_assets`

**Corps de la requête :**
```json
{
  "name": "DazCoin",
  "symbol": "DAZ",
  "total_supply": 21000000,
  "decimals": 8,
  "description": "Token natif du protocole Dazno"
}
```

**Réponse :**
```json
{
  "status": "success",
  "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
  "name": "DazCoin",
  "symbol": "DAZ",
  "total_supply": 21000000,
  "decimals": 8,
  "description": "Token natif du protocole Dazno",
  "created_at": "2025-08-23T12:00:00Z",
  "transaction_id": "tx_rgb1qvf8v5h9j3k2"
}
```

### 3. **Détails d'un asset** - `GET /api/v1/rgb/assets/{asset_id}`

Récupère les détails complets d'un asset RGB spécifique.

**Paramètres :**
- `asset_id` : Identifiant de l'asset RGB

**Réponse :**
```json
{
  "status": "success",
  "asset": {
    "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
    "name": "DazCoin",
    "symbol": "DAZ",
    "total_supply": 21000000,
    "circulating_supply": 15000000,
    "decimals": 8,
    "type": "token",
    "created_at": "2025-08-23T10:00:00Z",
    "contract_id": "contract_123",
    "issuer": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    "metadata": {
      "description": "Token natif du protocole Dazno",
      "website": "https://dazno.de",
      "logo": "https://dazno.de/logo.png"
    }
  },
  "timestamp": "2025-08-23T12:00:00Z"
}
```

---

## 💸 Transactions RGB

### 4. **Créer une transaction** - `POST /api/v1/rgb/transactions/create`

Crée une nouvelle transaction RGB pour transférer des assets.

**Permission requise :** `submit_transactions`

**Corps de la requête :**
```json
{
  "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
  "from_address": "bc1qw2e4r6t8y0u2i4o6p8a0s2d4f6g8h0j2k4l6m8n0",
  "to_address": "bc1qa2s4d6f8g0h2j4k6l8m0n2p4q6r8s0t2u4v6w8x0y2",
  "amount": 1000000,
  "fee_rate": 1
}
```

**Réponse :**
```json
{
  "status": "success",
  "transaction_id": "rgb_tx_a1b2c3d4e5f6789012345678901234567890abcd",
  "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
  "from_address": "bc1qw2e4r6t8y0u2i4o6p8a0s2d4f6g8h0j2k4l6m8n0",
  "to_address": "bc1qa2s4d6f8g0h2j4k6l8m0n2p4q6r8s0t2u4v6w8x0y2",
  "amount": 1000000,
  "fee_rate": 1,
  "created_at": "2025-08-23T12:00:00Z",
  "estimated_confirmation": "10-20 minutes",
  "bitcoin_tx_id": null
}
```

### 5. **Détails d'une transaction** - `GET /api/v1/rgb/transactions/{transaction_id}`

Récupère les détails d'une transaction RGB.

**Paramètres :**
- `transaction_id` : Identifiant de la transaction RGB

**Réponse :**
```json
{
  "status": "success",
  "transaction": {
    "transaction_id": "rgb_tx_a1b2c3d4e5f6789012345678901234567890abcd",
    "status": "confirmed",
    "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
    "from_address": "bc1qw2e4r6t8y0u2i4o6p8a0s2d4f6g8h0j2k4l6m8n0",
    "to_address": "bc1qa2s4d6f8g0h2j4k6l8m0n2p4q6r8s0t2u4v6w8x0y2",
    "amount": 1000000,
    "fee": 1000,
    "confirmations": 6,
    "bitcoin_tx_id": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "created_at": "2025-08-23T10:30:00Z",
    "confirmed_at": "2025-08-23T11:00:00Z"
  },
  "timestamp": "2025-08-23T12:00:00Z"
}
```

---

## 📜 Smart Contracts RGB

### 6. **Créer un contrat** - `POST /api/v1/rgb/contracts/create`

Déploie un nouveau smart contract RGB avec AluVM.

**Permission requise :** `deploy_contracts`

**Corps de la requête :**
```json
{
  "contract_type": "token",
  "name": "DazCoin Token",
  "parameters": {
    "total_supply": 21000000,
    "decimals": 8,
    "mintable": false
  },
  "initial_state": {
    "owner": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
  }
}
```

**Réponse :**
```json
{
  "status": "success",
  "contract_id": "contract_a1b2c3d4e5f6789012345678",
  "contract_type": "token",
  "name": "DazCoin Token",
  "parameters": {
    "total_supply": 21000000,
    "decimals": 8,
    "mintable": false
  },
  "initial_state": {
    "owner": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
  },
  "created_at": "2025-08-23T12:00:00Z",
  "deployment_tx": "deploy_contract_a1b2c3d4",
  "gas_estimate": 50000
}
```

### 7. **Liste des contrats** - `GET /api/v1/rgb/contracts/list`

Récupère la liste des smart contracts RGB déployés.

**Paramètres de requête :**
```
limit: int = 50          # Nombre maximum de contrats
offset: int = 0          # Décalage pour pagination
```

**Réponse :**
```json
{
  "status": "success",
  "contracts": [
    {
      "contract_id": "contract_123",
      "name": "DazCoin Token",
      "contract_type": "token",
      "created_at": "2025-08-23T10:00:00Z",
      "owner": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
      "status": "active"
    },
    {
      "contract_id": "contract_456",
      "name": "Lightning DEX",
      "contract_type": "defi",
      "created_at": "2025-08-23T09:00:00Z",
      "owner": "03abc123def456789012345678901234567890123456789012345678901234567890",
      "status": "active"
    }
  ],
  "total": 45,
  "limit": 50,
  "offset": 0,
  "timestamp": "2025-08-23T12:00:00Z"
}
```

---

## ✅ Validation RGB

### 8. **Valider une transaction** - `POST /api/v1/rgb/validate/transaction`

Valide une transaction RGB avant diffusion sur le réseau.

**Corps de la requête :**
```json
{
  "transaction_data": "02000000...",
  "contract_id": "contract_123"
}
```

**Réponse :**
```json
{
  "status": "success",
  "validation": {
    "valid": true,
    "transaction_id": "validation_a1b2c3d4e5f6789012345",
    "checks": {
      "signature_valid": true,
      "balance_sufficient": true,
      "contract_state_valid": true,
      "fee_adequate": true
    },
    "warnings": [],
    "estimated_fee": 1500,
    "timestamp": "2025-08-23T12:00:00Z"
  }
}
```

### 9. **Valider un contrat** - `POST /api/v1/rgb/validate/contract`

Valide le code d'un smart contract RGB avec AluVM.

**Corps de la requête :**
```json
{
  "contract_code": "contract DazCoin { ... }"
}
```

**Réponse :**
```json
{
  "status": "success",
  "validation": {
    "valid": true,
    "contract_hash": "hash_a1b2c3d4e5f6789012345",
    "checks": {
      "syntax_valid": true,
      "security_checks": true,
      "gas_estimation": 75000,
      "optimization_suggestions": []
    },
    "warnings": [],
    "timestamp": "2025-08-23T12:00:00Z"
  }
}
```

---

## ⚡ Intégration RGB++ Lightning

### 10. **Créer un canal RGB** - `POST /api/v1/rgb/lightning/channel/rgb`

Crée un canal Lightning avec support des assets RGB++.

**Permission requise :** `create_assets`

**Corps de la requête :**
```json
{
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
  "capacity": 5000000
}
```

**Réponse :**
```json
{
  "status": "success",
  "channel_id": "rgb_channel_a1b2c3d4e5f6789012345",
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
  "capacity": 5000000,
  "rgb_support": true,
  "created_at": "2025-08-23T12:00:00Z",
  "funding_tx": "funding_rgb_channel_a1b2"
}
```

### 11. **Canaux RGB d'un nœud** - `GET /api/v1/rgb/lightning/channels/{node_pubkey}`

Récupère tous les canaux Lightning RGB d'un nœud spécifique.

**Paramètres :**
- `node_pubkey` : Clé publique du nœud Lightning

**Réponse :**
```json
{
  "status": "success",
  "node_pubkey": "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
  "channels": [
    {
      "channel_id": "rgb_channel_123",
      "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
      "capacity": 5000000,
      "rgb_balance": 2500000,
      "bitcoin_balance": 2500000,
      "status": "active",
      "created_at": "2025-08-23T10:00:00Z"
    }
  ],
  "total_channels": 1,
  "timestamp": "2025-08-23T12:00:00Z"
}
```

---

## 🔍 Système et Monitoring

### 12. **Santé RGB** - `GET /api/v1/rgb/health`

Vérifie l'état de santé complet du système RGB.

**Réponse :**
```json
{
  "status": "healthy",
  "components": {
    "rgb_core": true,
    "rgb_standard": true,
    "aluvm": true,
    "bitcoin_node": true,
    "lightning_node": true
  },
  "version": "1.0.0",
  "timestamp": "2025-08-23T12:00:00Z"
}
```

### 13. **Statistiques RGB** - `GET /api/v1/rgb/stats`

Récupère les statistiques générales du système RGB.

**Réponse :**
```json
{
  "status": "success",
  "stats": {
    "total_assets": 125,
    "total_contracts": 45,
    "total_transactions": 3456,
    "active_channels": 89,
    "total_volume_24h": 15000000,
    "network_health": 0.95,
    "last_updated": "2025-08-23T12:00:00Z"
  }
}
```

---

## 🔒 Authentification et Sécurité

### Structure des tokens JWT

Les tokens JWT incluent les claims suivants :
```json
{
  "sub": "user_id",
  "username": "developer",
  "role": "developer",
  "permissions": ["read_assets", "create_assets", "deploy_contracts"],
  "iat": 1692792000,
  "exp": 1692795600,
  "iss": "mcp-rgb-api",
  "aud": "rgb-clients"
}
```

### API Keys

Format : `rgb_<32_caractères_aléatoires>`  
Exemple : `rgb_k8j3h2g1f9d8s7a6p5o4i3u2y1t0r9e8w7q6`

### Rate Limiting

- **Limite par défaut** : 100 requêtes/minute
- **Headers de réponse** :
  - `X-RateLimit-Limit` : Limite totale
  - `X-RateLimit-Remaining` : Requêtes restantes
  - `X-RateLimit-Reset` : Timestamp de reset

---

## 📊 Codes de réponse

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Ressource créée |
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Permission insuffisante |
| 404 | Ressource non trouvée |
| 429 | Limite de taux dépassée |
| 500 | Erreur serveur interne |
| 503 | Service indisponible |

---

## 🌐 Environnements supportés

### Testnet (par défaut)
- **URL** : `https://testnet.rgbpp.io/v1`
- **Authentification** : Aucune requise
- **Bitcoin** : Testnet3
- **Assets de test** : Disponibles

### Signet
- **URL** : `https://signet.rgbpp.io/v1`
- **Authentification** : Aucune requise
- **Bitcoin** : Signet
- **Assets de test** : Disponibles

### Mainnet
- **URL** : `https://api.rgbpp.io/v1`
- **Authentification** : Token JWT requis
- **Bitcoin** : Mainnet
- **Contact** : buidl@rgbpp.com pour accès

---

## 🚀 Exemples d'utilisation

### Créer un token RGB complet

```bash
# 1. Créer l'asset
curl -X POST https://api.dazno.de/api/v1/rgb/assets/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DazCoin",
    "symbol": "DAZ", 
    "total_supply": 21000000,
    "decimals": 8
  }'

# 2. Vérifier la création
curl -X GET https://api.dazno.de/api/v1/rgb/assets/rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2

# 3. Transférer des tokens
curl -X POST https://api.dazno.de/api/v1/rgb/transactions/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "rgb1qvf8v5h9j3k2l4m6n8p0q2r4s6t8u0v2w4y6z8a0b2",
    "from_address": "bc1q...",
    "to_address": "bc1q...",
    "amount": 1000000
  }'
```

### Déployer un smart contract DeFi

```bash
curl -X POST https://api.dazno.de/api/v1/rgb/contracts/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_type": "defi",
    "name": "Lightning DEX",
    "parameters": {
      "fee_rate": 30,
      "min_liquidity": 100000
    }
  }'
```

---

## 🔗 Liens utiles

- **RGB Protocol** : https://rgb.tech
- **RGB Core Library** : https://github.com/RGB-WG/rgb-core
- **RGB++ Assets API** : https://github.com/RGBPlusPlus/btc-assets-api
- **Documentation Swagger** : `https://api.dazno.de/docs`
- **Support** : support@dazno.de

---

## 📝 Notes importantes

1. **Sécurité** : Toujours valider les transactions avant diffusion
2. **Performance** : Utiliser le cache pour les assets fréquemment consultés  
3. **Rate Limiting** : Respecter les limites de taux pour éviter la restriction
4. **Mainnet** : Demander l'accès mainnet avant utilisation en production
5. **Updates** : Suivre les mises à jour du protocole RGB pour compatibilité

Cette documentation couvre l'intégration complète des APIs RGB dans le projet MCP, permettant la gestion des smart contracts Bitcoin et des assets RGB++ avec Lightning Network.