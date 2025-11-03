# 📘 Guide Technique - API MCP Production
> Documentation pour les équipes dazno.de
> Dernière mise à jour: 7 janvier 2025

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Authentification](#authentification)
3. [Configuration & Connexion](#configuration--connexion)
4. [Endpoints par Catégorie](#endpoints-par-catégorie)
5. [Exemples de Code](#exemples-de-code)
6. [Cas d'Usage Pratiques](#cas-dusage-pratiques)
7. [Gestion d'Erreurs](#gestion-derreurs)
8. [Best Practices](#best-practices)
9. [FAQ](#faq)

---

## 🎯 Introduction

### Qu'est-ce que l'API MCP ?

L'API MCP (Moniteur et Contrôleur de Performance) est une plateforme complète pour l'optimisation et l'analyse des nœuds Lightning Network. Elle offre des fonctionnalités avancées incluant :

- 💰 **Gestion de portefeuille Lightning** via LNbits
- 🔗 **Recommandations de canaux** intelligentes
- ⚡ **Analyse avancée** du réseau Lightning
- 🤖 **Chatbot IA** avec analyse contextuelle
- 📊 **Analytics DazFlow** pour évaluer les performances
- 🔍 **Système RAG** pour recherche sémantique
- ⚙️ **Optimisation automatique** des frais
- 🧠 **Intelligence artificielle** pour recommandations

### Base URL

```
Production:  https://api.dazno.de
Développement: http://localhost:8000
```

### Format des Réponses

Toutes les réponses sont au format **JSON** avec la structure suivante :

```json
{
  "status": "success|error",
  "data": { ... },
  "message": "Description optionnelle",
  "request_id": "req_1234567890"
}
```

---

## 🔐 Authentification

### Vue d'ensemble

La plupart des endpoints nécessitent une **authentification JWT**. Le token doit être inclus dans le header `Authorization` au format Bearer.

### Format du Token

```
Authorization: Bearer <votre_jwt_token>
```

### Structure du JWT

Le token JWT doit contenir au minimum :

```json
{
  "tenant_id": "votre_tenant_id",
  "sub": "user_id_ou_tenant_id",
  "iss": "app.dazno.de",
  "aud": "api.dazno.de",
  "exp": 1234567890
}
```

### Obtenir un Token

Pour obtenir un token JWT valide, contactez l'équipe DevOps ou utilisez votre système d'authentification interne dazno.de.

### Vérification du Token

Le système vérifie automatiquement :
- ✅ Validité de la signature
- ✅ Date d'expiration
- ✅ Émetteur (iss) : `app.dazno.de`
- ✅ Audience (aud) : `api.dazno.de`
- ✅ Isolation multi-tenant via `tenant_id`

### Exemple d'Authentification

```bash
# cURL
curl -X GET "https://api.dazno.de/api/v1/nodes/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

```python
# Python
import requests

headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.dazno.de/api/v1/nodes/",
    headers=headers
)
```

```javascript
// JavaScript/TypeScript
const response = await fetch('https://api.dazno.de/api/v1/nodes/', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json'
  }
});
```

---

## ⚙️ Configuration & Connexion

### Endpoints Publics (Pas d'authentification)

Ces endpoints peuvent être appelés sans JWT :

- `GET /` - Informations API
- `GET /info` - Informations système
- `GET /health` - Health check basique
- `GET /health/detailed` - Santé détaillée
- `GET /metrics/prometheus` - Métriques Prometheus

### Test de Connexion Rapide

```bash
# Test de santé
curl https://api.dazno.de/health

# Test avec authentification
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.dazno.de/api/v1/status
```

---

## 📚 Endpoints par Catégorie

### 🏥 Health & Monitoring

#### Health Checks

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/health` | GET | ❌ | Vérification de santé basique |
| `/health/detailed` | GET | ❌ | Santé détaillée avec composants |
| `/health/components` | GET | ❌ | État individuel des composants |
| `/health/ready` | GET | ❌ | Probe Kubernetes/Docker |
| `/health/live` | GET | ❌ | Probe de vitalité |

**Exemple :**
```bash
curl https://api.dazno.de/health/detailed
```

**Réponse :**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-07T12:00:00Z",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "lnbits": "healthy"
  }
}
```

#### Métriques

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/metrics/prometheus` | GET | ❌ | Export Prometheus |
| `/metrics/dashboard` | GET | ❌ | Dashboard complet |
| `/metrics/performance` | GET | ❌ | Métriques de performance |

---

### 💰 Wallet Lightning (LNbits)

#### Obtenir le Solde

```bash
curl -X GET "https://api.dazno.de/api/v1/wallet/balance" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse :**
```json
{
  "id": "wallet_abc123",
  "name": "Mon Wallet Principal",
  "balance": 125000,
  "currency": "sats",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### Créer une Facture Lightning

```bash
curl -X POST "https://api.dazno.de/api/v1/wallet/invoice" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50000,
    "memo": "Paiement pour service"
  }'
```

**Réponse :**
```json
{
  "payment_hash": "abc123...",
  "payment_request": "lnbc500u1p...",
  "amount": 50000,
  "expires_at": "2025-01-07T13:00:00Z"
}
```

#### Payer une Facture

```bash
curl -X POST "https://api.dazno.de/api/v1/wallet/pay" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bolt11": "lnbc500u1p..."
  }'
```

---

### 🌐 Gestion des Nœuds

#### Créer un Nœud

```bash
curl -X POST "https://api.dazno.de/api/v1/nodes/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pubkey": "02b1fe652cfc...",
    "alias": "Mon Nœud",
    "host": "node.example.com",
    "port": 9735
  }'
```

#### Lister les Nœuds

```bash
curl -X GET "https://api.dazno.de/api/v1/nodes/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse :**
```json
[
  {
    "_id": "65a1b2c3d4e5f6g7h8i9j0k1",
    "pubkey": "02b1fe652cfc...",
    "alias": "Mon Nœud",
    "tenant_id": "tenant_123",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

#### Obtenir un Nœud Spécifique

```bash
# Par ID MongoDB
curl "https://api.dazno.de/api/v1/nodes/65a1b2c3d4e5f6g7h8i9j0k1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Par Pubkey
curl "https://api.dazno.de/api/v1/nodes/02b1fe652cfc..." \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### ⚡ Lightning Network - Analyse Avancée

#### Analyse d'un Nœud

```bash
curl "https://api.dazno.de/api/v1/lightning/nodes/02b1fe652cfc.../enhanced-analysis" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse inclut :**
- Métriques de centralité
- Analyse financière
- Score de performance
- Recommandations

#### Probabilité de Paiement

```bash
curl "https://api.dazno.de/api/v1/lightning/payment-probability/02b1fe652cfc.../03a81c5aa298..." \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse :**
```json
{
  "source_node": "02b1fe652cfc...",
  "target_node": "03a81c5aa298...",
  "probability": 0.92,
  "optimal_path": [...],
  "max_flow": 5000000
}
```

---

### 📊 Analytics DazFlow

#### Indice DazFlow d'un Nœud

```bash
curl "https://api.dazno.de/analytics/dazflow/node/65a1b2c3d4e5f6g7h8i9j0k1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Réponse :**
```json
{
  "node_id": "65a1b2c3d4e5f6g7h8i9j0k1",
  "dazflow_index": 85.5,
  "metrics": {
    "liquidity_score": 0.92,
    "centrality_score": 0.88,
    "fee_efficiency": 0.90
  },
  "recommendations": [...]
}
```

---

### 🔍 Système RAG

#### Requête RAG

```bash
curl -X POST "https://api.dazno.de/api/v1/rag/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Comment optimiser les frais de mon nœud ?",
    "max_results": 5,
    "context_type": "lightning",
    "include_validation": true
  }'
```

**Réponse :**
```json
{
  "status": "success",
  "answer": "Analyse détaillée de l'optimisation...",
  "sources": ["doc1", "doc2"],
  "confidence": 0.92,
  "validation": "Validation Ollama...",
  "processing_time": 1.2
}
```

#### Analyser un Nœud avec RAG

```bash
curl -X POST "https://api.dazno.de/api/v1/rag/analyze/node" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_pubkey": "02b1fe652cfc...",
    "analysis_type": "performance",
    "time_range": "7d",
    "include_recommendations": true
  }'
```

---

### 🤖 Chatbot IA

#### Poser une Question

```bash
curl -X POST "https://api.dazno.de/api/v1/chatbot/ask" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels sont les principaux goulots d'étranglement de mon nœud ?",
    "node_pubkey": "02b1fe652cfc...",
    "context": "lightning_network"
  }'
```

#### Résumé d'un Nœud

```bash
curl "https://api.dazno.de/api/v1/chatbot/node-summary/02b1fe652cfc..." \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### ⚙️ Optimisation de Frais

#### Lancer une Optimisation

```bash
curl -X POST "https://api.dazno.de/api/v1/fee-optimizer/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_ids": ["node_id_1"],
    "dry_run": true,
    "max_updates": 10
  }'
```

**Réponse :**
```json
{
  "success": true,
  "message": "Optimisation lancée avec succès",
  "updates": [
    {
      "channel_id": "channel_123",
      "old_base_fee": 1000,
      "new_base_fee": 1500,
      "old_fee_rate": 500,
      "new_fee_rate": 600,
      "reason": "Taux de succès élevé, augmentation recommandée"
    }
  ],
  "timestamp": "2025-01-07T12:00:00Z"
}
```

#### Rollback des Changements

```bash
curl -X POST "https://api.dazno.de/api/v1/fee-optimizer/rollback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "updates_id": "update_123",
    "reason": "Performance dégradée après modification"
  }'
```

---

## 💻 Exemples de Code

### Python - Client API Complet

```python
import requests
from typing import Optional, Dict, List

class MCPClient:
    """Client Python pour l'API MCP"""
    
    def __init__(self, base_url: str = "https://api.dazno.de", token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Méthode générique pour les requêtes"""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # Health
    def get_health(self) -> Dict:
        return self._request("GET", "/health")
    
    # Wallet
    def get_wallet_balance(self) -> Dict:
        return self._request("GET", "/api/v1/wallet/balance")
    
    def create_invoice(self, amount: int, memo: str = "") -> Dict:
        return self._request("POST", "/api/v1/wallet/invoice", json={
            "amount": amount,
            "memo": memo
        })
    
    # Nodes
    def list_nodes(self) -> List[Dict]:
        return self._request("GET", "/api/v1/nodes/")
    
    def get_node(self, node_id: str) -> Dict:
        return self._request("GET", f"/api/v1/nodes/{node_id}")
    
    def create_node(self, node_data: Dict) -> Dict:
        return self._request("POST", "/api/v1/nodes/", json=node_data)
    
    # Analytics
    def get_dazflow_index(self, node_id: str) -> Dict:
        return self._request("GET", f"/analytics/dazflow/node/{node_id}")
    
    # RAG
    def rag_query(self, query: str, max_results: int = 5) -> Dict:
        return self._request("POST", "/api/v1/rag/query", json={
            "query": query,
            "max_results": max_results,
            "context_type": "lightning"
        })
    
    # Fee Optimizer
    def optimize_fees(self, node_ids: List[str], dry_run: bool = True) -> Dict:
        return self._request("POST", "/api/v1/fee-optimizer/optimize", json={
            "node_ids": node_ids,
            "dry_run": dry_run
        })

# Utilisation
client = MCPClient(token="votre_jwt_token")
balance = client.get_wallet_balance()
nodes = client.list_nodes()
```

### JavaScript/TypeScript

```typescript
class MCPClient {
  private baseUrl: string;
  private token: string | null;
  
  constructor(baseUrl: string = "https://api.dazno.de", token?: string) {
    this.baseUrl = baseUrl;
    this.token = token || null;
  }
  
  private async request<T>(
    method: string,
    endpoint: string,
    body?: any
  ): Promise<T> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  // Health
  async getHealth() {
    return this.request("/health");
  }
  
  // Wallet
  async getWalletBalance() {
    return this.request("/api/v1/wallet/balance");
  }
  
  async createInvoice(amount: number, memo: string = "") {
    return this.request("/api/v1/wallet/invoice", {
      method: "POST",
      body: { amount, memo },
    });
  }
  
  // Nodes
  async listNodes() {
    return this.request("/api/v1/nodes/");
  }
  
  async getNode(nodeId: string) {
    return this.request(`/api/v1/nodes/${nodeId}`);
  }
  
  // Analytics
  async getDazflowIndex(nodeId: string) {
    return this.request(`/analytics/dazflow/node/${nodeId}`);
  }
  
  // RAG
  async ragQuery(query: string, maxResults: number = 5) {
    return this.request("/api/v1/rag/query", {
      method: "POST",
      body: {
        query,
        max_results: maxResults,
        context_type: "lightning",
      },
    });
  }
}

// Utilisation
const client = new MCPClient("https://api.dazno.de", "votre_jwt_token");
const balance = await client.getWalletBalance();
const nodes = await client.listNodes();
```

---

## 📖 Cas d'Usage Pratiques

### Cas 1 : Vérifier l'État d'un Nœud

```python
client = MCPClient(token="YOUR_TOKEN")

# 1. Obtenir les informations du nœud
node = client.get_node("node_id_123")

# 2. Obtenir l'indice DazFlow
dazflow = client.get_dazflow_index("node_id_123")

# 3. Obtenir l'analyse Lightning
analysis = client._request(
    "GET",
    f"/api/v1/lightning/nodes/{node['pubkey']}/enhanced-analysis"
)

print(f"Nœud: {node['alias']}")
print(f"DazFlow Index: {dazflow['dazflow_index']}")
print(f"Score de performance: {analysis['performance_score']}")
```

### Cas 2 : Optimiser les Frais Automatiquement

```python
import schedule
import time

def optimize_node_fees():
    client = MCPClient(token="YOUR_TOKEN")
    
    # 1. Lister tous les nœuds
    nodes = client.list_nodes()
    
    # 2. Pour chaque nœud, lancer l'optimisation
    for node in nodes:
        result = client.optimize_fees(
            node_ids=[node["_id"]],
            dry_run=False  # Mode production
        )
        print(f"Optimisation {node['alias']}: {result['message']}")

# Exécuter tous les jours à 2h du matin
schedule.every().day.at("02:00").do(optimize_node_fees)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Cas 3 : Monitorer la Santé du Réseau

```python
def monitor_network_health():
    client = MCPClient(token="YOUR_TOKEN")
    
    # 1. Health check global
    health = client.get_health()
    
    # 2. Santé détaillée
    detailed = client._request("GET", "/health/detailed")
    
    # 3. Métriques Prometheus
    metrics = client._request("GET", "/metrics/prometheus")
    
    # Analyser et alerter si nécessaire
    if health["status"] != "healthy":
        send_alert(f"Système en état dégradé: {health}")
    
    return {
        "health": health,
        "detailed": detailed,
        "metrics": metrics
    }
```

### Cas 4 : Analyse RAG d'un Nœud avec Recommandations

```python
def analyze_node_with_rag(node_pubkey: str):
    client = MCPClient(token="YOUR_TOKEN")
    
    # 1. Question au chatbot
    question = f"Quels sont les principaux problèmes de performance du nœud {node_pubkey}?"
    chatbot_response = client._request(
        "POST",
        "/api/v1/chatbot/ask",
        json={
            "question": question,
            "node_pubkey": node_pubkey
        }
    )
    
    # 2. Analyse RAG complète
    rag_analysis = client._request(
        "POST",
        "/api/v1/rag/analyze/node",
        json={
            "node_pubkey": node_pubkey,
            "analysis_type": "performance",
            "time_range": "7d",
            "include_recommendations": True
        }
    )
    
    return {
        "chatbot_insights": chatbot_response,
        "rag_analysis": rag_analysis,
        "recommendations": rag_analysis.get("recommendations", [])
    }
```

---

## 🚨 Gestion d'Erreurs

### Codes de Statut HTTP

| Code | Signification | Action Recommandée |
|------|---------------|-------------------|
| `200` | Succès | Traiter la réponse normalement |
| `201` | Créé | Ressource créée avec succès |
| `400` | Requête invalide | Vérifier les paramètres |
| `401` | Non authentifié | Vérifier le token JWT |
| `403` | Interdit | Vérifier les permissions |
| `404` | Non trouvé | Vérifier l'ID de la ressource |
| `409` | Conflit | Ressource existe déjà |
| `429` | Trop de requêtes | Réduire la fréquence |
| `500` | Erreur serveur | Contacter le support |
| `503` | Service indisponible | Réessayer plus tard |

### Format des Erreurs

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Paramètre invalide",
    "details": {
      "field": "amount",
      "reason": "Montant doit être supérieur à 0"
    }
  },
  "request_id": "req_1234567890"
}
```

### Gestion d'Erreurs en Python

```python
from requests.exceptions import HTTPError, RequestException

try:
    response = client.get_wallet_balance()
except HTTPError as e:
    if e.response.status_code == 401:
        print("Token expiré, renouveler l'authentification")
    elif e.response.status_code == 429:
        print("Rate limit atteint, attendre avant de réessayer")
        time.sleep(60)
    else:
        error_data = e.response.json()
        print(f"Erreur: {error_data['error']['message']}")
except RequestException as e:
    print(f"Erreur de connexion: {e}")
```

### Retry Logic

```python
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except HTTPError as e:
                    if e.response.status_code >= 500 and attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                    raise
            return None
        return wrapper
    return decorator

@retry_on_error(max_retries=3, delay=2)
def get_node_with_retry(client, node_id):
    return client.get_node(node_id)
```

---

## ✅ Best Practices

### 1. Authentification

✅ **DO**
- Stocker le token de manière sécurisée (variables d'environnement)
- Renouveler le token avant expiration
- Utiliser HTTPS uniquement en production

❌ **DON'T**
- Exposer le token dans le code source
- Utiliser le même token pour tous les environnements
- Partager le token entre équipes sans autorisation

### 2. Rate Limiting

✅ **DO**
- Implémenter un backoff exponentiel
- Respecter les limites de taux (429)
- Mettre en cache les réponses quand possible

❌ **DON'T**
- Faire des requêtes en boucle sans délai
- Ignorer les codes 429
- Faire trop de requêtes simultanées

### 3. Gestion des Erreurs

✅ **DO**
- Toujours vérifier les codes de statut
- Logger les erreurs avec le `request_id`
- Implémenter une logique de retry intelligente

❌ **DON'T**
- Ignorer les erreurs silencieusement
- Afficher les tokens dans les logs
- Faire des retries infinis

### 4. Performance

✅ **DO**
- Utiliser les endpoints de pagination
- Mettre en cache les données statiques
- Faire des requêtes en parallèle quand possible

❌ **DON'T**
- Récupérer toutes les données à chaque fois
- Faire des requêtes inutiles
- Bloquer l'interface pendant les requêtes

### 5. Sécurité

✅ **DO**
- Valider tous les inputs côté client
- Utiliser HTTPS uniquement
- Sanitizer les données avant envoi

❌ **DON'T**
- Envoyer des données sensibles sans chiffrement
- Faire confiance aux inputs utilisateurs
- Exposer les tokens dans l'URL

---

## ❓ FAQ

### Q: Comment obtenir un token JWT ?

**R:** Contactez l'équipe DevOps dazno.de ou utilisez votre système d'authentification interne. Les tokens sont générés par `app.dazno.de`.

### Q: Quelle est la durée de vie d'un token ?

**R:** Les tokens ont généralement une durée de vie de 24 heures. Vérifiez le champ `exp` dans le payload JWT.

### Q: Comment renouveler un token expiré ?

**R:** Utilisez votre système d'authentification pour obtenir un nouveau token. Le système ne fournit pas d'endpoint de refresh automatique.

### Q: Quelle est la limite de taux ?

**R:** Les limites varient selon l'endpoint et le tenant. En cas de dépassement, vous recevrez un code 429. Implémentez un backoff exponentiel.

### Q: Les endpoints sont-ils idempotents ?

**R:** La plupart des endpoints GET sont idempotents. Les POST peuvent nécessiter une vérification pour éviter les doublons.

### Q: Comment isoler les données par tenant ?

**R:** Le système isole automatiquement les données par `tenant_id` extrait du JWT. Chaque tenant ne voit que ses propres données.

### Q: Peut-on utiliser l'API en production immédiatement ?

**R:** Oui, l'API est disponible en production sur `https://api.dazno.de`. Assurez-vous d'avoir un token JWT valide.

### Q: Y a-t-il une documentation interactive ?

**R:** La documentation Swagger (`/docs`) est désactivée en production pour sécurité. Utilisez cette documentation technique.

### Q: Comment contacter le support ?

**R:** 
- Email: support@dazno.de
- Website: https://dazno.de
- Pour les questions techniques, contactez l'équipe DevOps

---

## 📞 Support & Contact

- **Email Support**: support@dazno.de
- **Website**: https://dazno.de
- **Documentation Technique**: Cette documentation
- **Issues Techniques**: Contactez l'équipe DevOps dazno.de

---

**Document Version**: 1.0  
**Last Updated**: 7 janvier 2025  
**Maintained by**: Équipe MCP dazno.de

